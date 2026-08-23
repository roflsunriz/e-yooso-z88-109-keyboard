"""E-YOOSO Z88 109のHID構成を変更せずに読み取る。"""

from __future__ import annotations

import sys
from typing import Any


VENDOR_ID = 0x258A
PRODUCT_ID = 0x0049


def path_text(path: bytes | str) -> str:
    if isinstance(path, bytes):
        return path.decode(errors="replace")
    return path


def find_collection(
    devices: list[dict[str, Any]], collection: str
) -> dict[str, Any]:
    matches = [
        device
        for device in devices
        if collection in path_text(device.get("path", "")).lower()
    ]
    if len(matches) != 1:
        raise RuntimeError(f"{collection}の候補数が{len(matches)}件です")
    return matches[0]


def main() -> int:
    try:
        import hid
    except ImportError as error:
        print(f"hidapiを読み込めません: {error}", file=sys.stderr)
        return 2

    devices = hid.enumerate(VENDOR_ID, PRODUCT_ID)
    print(f"VID={VENDOR_ID:04X} PID={PRODUCT_ID:04X} collections={len(devices)}")
    for index, device in enumerate(devices):
        print(
            f"[{index}] interface={device.get('interface_number')} "
            f"usage_page=0x{device.get('usage_page', 0):04X} "
            f"usage=0x{device.get('usage', 0):04X} "
            f"path={path_text(device.get('path', ''))}"
        )

    try:
        report5_info = find_collection(devices, "col05")
        report5 = hid.device()
        report5.open_path(report5_info["path"])
        current = bytes(report5.get_feature_report(0x05, 6))
        report5.close()
        if len(current) != 6 or current[0] != 0x05:
            raise OSError(f"Report 5の現在値が不正です: {current.hex(' ')}")
        print(f"Report 5現在値: {current.hex(' ')}")
    except Exception as error:
        print(f"Report 5の読み取りに失敗しました: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
