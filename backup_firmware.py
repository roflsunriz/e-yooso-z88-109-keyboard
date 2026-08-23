"""E-YOOSO Z88 109のファームウェアをフラッシュ変更なしで退避する。"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import isp_protocol
from probe_device import PRODUCT_ID, VENDOR_ID, path_text
from runtime_paths import activate_local_dependencies


activate_local_dependencies()


ISP_VENDOR_ID = 0x0603
ISP_PRODUCT_IDS = (0x1020, 0x1021)
FIRMWARE_SIZE = 61_440
PAGE_SIZE = 2_048
APP_COLLECTION = "col05"
WAIT_SECONDS = 8.0


def report_ids_from_descriptor(descriptor: bytes) -> set[int]:
    """HID short item列からReport IDを抽出する。"""
    result: set[int] = set()
    offset = 0
    while offset < len(descriptor):
        prefix = descriptor[offset]
        offset += 1
        if prefix == 0xFE:
            if offset + 2 > len(descriptor):
                raise ValueError("HID long itemヘッダーが途中で終わっています")
            size = descriptor[offset]
            offset += 2 + size
            continue

        size_code = prefix & 0x03
        size = 4 if size_code == 3 else size_code
        item_type = (prefix >> 2) & 0x03
        tag = (prefix >> 4) & 0x0F
        if offset + size > len(descriptor):
            raise ValueError("HID short itemが途中で終わっています")
        data = descriptor[offset : offset + size]
        if item_type == 1 and tag == 8 and size == 1:
            result.add(data[0])
        offset += size
    return result


def find_app_command_device(hid_module: Any) -> dict[str, Any]:
    matches = []
    for device in hid_module.enumerate(VENDOR_ID, PRODUCT_ID):
        if (
            device.get("interface_number") == 1
            and APP_COLLECTION in path_text(device.get("path", "")).lower()
        ):
            matches.append(device)
    if len(matches) != 1:
        raise RuntimeError(f"Z88の{APP_COLLECTION}候補数が{len(matches)}件です")
    return matches[0]


def descriptor_report_ids(hid_module: Any, device_info: dict[str, Any]) -> set[int]:
    device = hid_module.device()
    try:
        device.open_path(device_info["path"])
        return report_ids_from_descriptor(bytes(device.get_report_descriptor()))
    finally:
        device.close()


def find_isp_paths(hid_module: Any) -> tuple[bytes | str, bytes | str] | None:
    command_matches: list[bytes | str] = []
    transfer_matches: list[bytes | str] = []
    for product_id in ISP_PRODUCT_IDS:
        for device in hid_module.enumerate(ISP_VENDOR_ID, product_id):
            if device.get("interface_number") != 0:
                continue
            report_ids = descriptor_report_ids(hid_module, device)
            if isp_protocol.REPORT_ID_COMMAND in report_ids:
                command_matches.append(device["path"])
            if isp_protocol.REPORT_ID_TRANSFER in report_ids:
                transfer_matches.append(device["path"])

    if not command_matches and not transfer_matches:
        return None
    if len(command_matches) != 1 or len(transfer_matches) != 1:
        raise RuntimeError(
            "ISPのReport 5/6を一意に特定できません: "
            f"Report 5={len(command_matches)}件、Report 6={len(transfer_matches)}件"
        )
    return command_matches[0], transfer_matches[0]


def wait_for_isp_paths(hid_module: Any) -> tuple[bytes | str, bytes | str]:
    deadline = time.monotonic() + WAIT_SECONDS
    while time.monotonic() < deadline:
        paths = find_isp_paths(hid_module)
        if paths is not None:
            return paths
        time.sleep(0.2)
    raise TimeoutError("8秒以内にSinowealth ISPデバイスを検出できませんでした")


def wait_for_application(hid_module: Any) -> None:
    deadline = time.monotonic() + WAIT_SECONDS
    while time.monotonic() < deadline:
        try:
            find_app_command_device(hid_module)
            return
        except RuntimeError:
            time.sleep(0.2)
    raise TimeoutError("再起動後にZ88が通常モードへ戻りませんでした")


def save_dump(output_path: Path, firmware: bytes) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(firmware)
    digest = hashlib.sha256(firmware).hexdigest()
    metadata = {
        "vendor_id": f"0x{VENDOR_ID:04X}",
        "product_id": f"0x{PRODUCT_ID:04X}",
        "firmware_size": len(firmware),
        "sha256": digest,
        "read_method": "ISP commands 0x75, 0x52, 0x5A only; no 0x55/erase/write",
    }
    output_path.with_suffix(output_path.suffix + ".json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"保存しました: {output_path} ({len(firmware)} bytes, SHA256={digest})")


def read_from_device(hid_module: Any, output_path: Path) -> None:
    app_info = find_app_command_device(hid_module)
    app = hid_module.device()
    app.open_path(app_info["path"])
    try:
        print("ISPモードへ移行します（Report 5: 05 75 00 00 00 00）。")
        try:
            isp_protocol.send_command(app, isp_protocol.COMMAND_ENTER_ISP)
        except OSError:
            # Windowsでは再列挙により送信完了時にハンドルが切れる場合がある。
            pass
    finally:
        app.close()

    command_path, transfer_path = wait_for_isp_paths(hid_module)
    command_device = hid_module.device()
    transfer_device = hid_module.device()
    firmware: bytes | None = None
    reboot_error: Exception | None = None
    try:
        command_device.open_path(command_path)
        transfer_device.open_path(transfer_path)
        print("フラッシュを30ページ読み取ります。書換え命令0x55/0x57/0x45は送りません。")
        firmware = isp_protocol.read_firmware(
            command_device,
            transfer_device,
            firmware_size=FIRMWARE_SIZE,
            page_size=PAGE_SIZE,
            progress=lambda done, total: print(f"読出し: {done}/{total}"),
        )
    finally:
        try:
            print("通常モードへ再起動します（Report 5: 05 5A 00 00 00 00）。")
            isp_protocol.send_command(command_device, isp_protocol.COMMAND_REBOOT)
        except Exception as error:
            reboot_error = error
        transfer_device.close()
        command_device.close()

    if firmware is None:
        raise RuntimeError("ファームウェアを取得できませんでした")
    save_dump(output_path, firmware)

    try:
        wait_for_application(hid_module)
    except TimeoutError as error:
        if find_isp_paths(hid_module) is None:
            detail = f" ({reboot_error})" if reboot_error is not None else ""
            print(
                "バックアップは成功しましたが、USBデバイスが切断状態です"
                f"{detail}。ケーブルを抜き差ししてください。",
                file=sys.stderr,
            )
            return
        raise
    print("Z88が通常モードへ復帰したことを確認しました。")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Z88 109のファームウェアを破壊的コマンドなしで退避します。"
    )
    parser.add_argument(
        "--read-firmware",
        action="store_true",
        help="ISPへ一時移行し、61,440バイトを読み取って再起動します。",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("firmware-dumps/z88-109-firmware.bin"),
        help="出力先（既定値: firmware-dumps/z88-109-firmware.bin）",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        import hid
    except ImportError as error:
        print(f"hidapiを読み込めません: {error}", file=sys.stderr)
        return 2

    try:
        app_info = find_app_command_device(hid)
        report_ids = descriptor_report_ids(hid, app_info)
        if report_ids != {isp_protocol.REPORT_ID_COMMAND}:
            raise RuntimeError(f"Col05のReport IDが想定外です: {sorted(report_ids)}")
        print(
            "対象確認: "
            f"VID={VENDOR_ID:04X} PID={PRODUCT_ID:04X} "
            f"path={path_text(app_info['path'])}"
        )
        print("禁止コマンド: 0x55 (LJMP変更), 0x57 (書込み), 0x45 (消去)")
        if not args.read_firmware:
            print("dry-run完了。実機の状態変更やファイル出力は行っていません。")
            return 0
        read_from_device(hid, args.output)
        return 0
    except Exception as error:
        print(f"ファームウェア退避失敗: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
