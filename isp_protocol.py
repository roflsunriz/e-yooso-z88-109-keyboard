"""Sinowealth ISPの非破壊読出しに必要な最小プロトコル。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol


REPORT_ID_COMMAND = 0x05
REPORT_ID_TRANSFER = 0x06
COMMAND_ENTER_ISP = 0x75
COMMAND_INIT_READ = 0x52
COMMAND_REBOOT = 0x5A
TRANSFER_READ_PAGE = 0x72
COMMAND_LENGTH = 6


class FeatureDevice(Protocol):
    def send_feature_report(self, data: bytes) -> int: ...

    def get_feature_report(self, report_id: int, length: int) -> list[int]: ...


def command(opcode: int, address: int = 0) -> bytes:
    """許可済みの非破壊コマンドだけを6バイトReport 5へ符号化する。"""
    allowed = {COMMAND_ENTER_ISP, COMMAND_INIT_READ, COMMAND_REBOOT}
    if opcode not in allowed:
        raise ValueError(f"許可されていないISPコマンドです: 0x{opcode:02X}")
    if not 0 <= address <= 0xFFFF:
        raise ValueError(f"アドレスが範囲外です: {address}")
    return bytes(
        (REPORT_ID_COMMAND, opcode, address & 0xFF, (address >> 8) & 0xFF, 0, 0)
    )


def send_command(device: FeatureDevice, opcode: int, address: int = 0) -> None:
    payload = command(opcode, address)
    sent = device.send_feature_report(payload)
    if sent != COMMAND_LENGTH:
        raise OSError(
            f"Report 5の送信長が不正です: {sent} (期待値: {COMMAND_LENGTH})"
        )


def read_firmware(
    command_device: FeatureDevice,
    transfer_device: FeatureDevice,
    *,
    firmware_size: int,
    page_size: int,
    progress: Callable[[int, int], None] | None = None,
) -> bytes:
    """フラッシュを変更せず、Report 6でファームウェア領域を読む。"""
    if firmware_size <= 0 or page_size <= 0 or firmware_size % page_size != 0:
        raise ValueError("firmware_sizeはpage_sizeの正の整数倍である必要があります")

    send_command(command_device, COMMAND_INIT_READ, 0)
    total_pages = firmware_size // page_size
    output = bytearray()

    for page_index in range(total_pages):
        report = bytes(
            transfer_device.get_feature_report(
                REPORT_ID_TRANSFER,
                page_size + 2,
            )
        )
        if len(report) != page_size + 2:
            raise OSError(
                f"Report 6の受信長が不正です: {len(report)} "
                f"(期待値: {page_size + 2})"
            )
        if report[0] != REPORT_ID_TRANSFER or report[1] != TRANSFER_READ_PAGE:
            raise OSError(
                "Report 6の応答ヘッダーが不正です: "
                f"{report[:2].hex(' ')} (期待値: 06 72)"
            )
        output.extend(report[2:])
        if progress is not None:
            progress(page_index + 1, total_pages)

    return bytes(output)
