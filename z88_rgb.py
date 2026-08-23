"""E-YOOSO Z88 109のBYK916動画モードを制御する。"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from typing import Any

from probe_device import PRODUCT_ID, VENDOR_ID, path_text


Color = tuple[int, int, int]
REPORT_ID = 0x08
PACKET_LENGTH = 382
PACKET_HEADER = bytes((0x08, 0x0A, 0x7A, 0x01))
RGB_SLOT_COUNT = 126
VIDEO_MODE_INITIALIZATION_COUNT = 3
VIDEO_MODE_INTERVAL_SECONDS = 0.016


def validate_color(color: Color) -> None:
    if len(color) != 3 or any(component < 0 or component > 255 for component in color):
        raise ValueError(f"RGB値が不正です: {color}")


def build_packet(colors: Sequence[Color]) -> bytes:
    if len(colors) != RGB_SLOT_COUNT:
        raise ValueError(
            f"RGBスロット数が不正です: {len(colors)} (期待値: {RGB_SLOT_COUNT})"
        )
    body = bytearray()
    for color in colors:
        validate_color(color)
        body.extend(color)
    packet = PACKET_HEADER + body
    if len(packet) != PACKET_LENGTH:
        raise AssertionError(f"Report 8の長さが不正です: {len(packet)}")
    return bytes(packet)


def uniform_frame(color: Color) -> list[Color]:
    validate_color(color)
    return [color] * RGB_SLOT_COUNT


def find_report8_device(hid_module: Any) -> dict[str, Any]:
    matches = [
        device
        for device in hid_module.enumerate(VENDOR_ID, PRODUCT_ID)
        if device.get("interface_number") == 1
        and "col08" in path_text(device.get("path", "")).lower()
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Z88のCol08候補数が{len(matches)}件です")
    return matches[0]


class Z88RGBController:
    def __init__(
        self,
        hid_module: Any,
        pause: Callable[[float], None] = time.sleep,
    ) -> None:
        self._hid = hid_module
        self._pause = pause
        self._device: Any | None = None
        self._initialized = False

    def open(self) -> None:
        if self._device is not None:
            return
        info = find_report8_device(self._hid)
        device = self._hid.device()
        device.open_path(info["path"])
        self._device = device

    def close(self) -> None:
        if self._device is None:
            return
        self._device.close()
        self._device = None
        self._initialized = False

    def _send(self, packet: bytes) -> None:
        if self._device is None:
            raise RuntimeError("Z88を開いていません")
        sent = self._device.send_feature_report(packet)
        if sent != PACKET_LENGTH:
            raise OSError(
                f"Report 8の送信長が不正です: {sent} (期待値: {PACKET_LENGTH})"
            )

    def initialize_video_mode(self) -> None:
        if self._initialized:
            return
        zero_packet = build_packet(uniform_frame((0, 0, 0)))
        for _ in range(VIDEO_MODE_INITIALIZATION_COUNT):
            self._send(zero_packet)
            self._pause(VIDEO_MODE_INTERVAL_SECONDS)
        self._initialized = True

    def send_frame(self, colors: Sequence[Color], *, initialize: bool = True) -> None:
        if initialize and not self._initialized:
            self.initialize_video_mode()
        self._send(build_packet(colors))

    def set_uniform(self, color: Color, *, initialize: bool = True) -> None:
        self.send_frame(uniform_frame(color), initialize=initialize)

    def off(self) -> None:
        self.send_frame(uniform_frame((0, 0, 0)))

    def __enter__(self) -> "Z88RGBController":
        self.open()
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.close()
