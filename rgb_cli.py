"""Z88の直接RGB制御を確認・利用するCLI。"""

from __future__ import annotations

import argparse
import colorsys
import sys
import time
from collections.abc import Sequence

import z88_rgb
from runtime_paths import activate_local_dependencies


activate_local_dependencies()


def parse_color(value: str) -> z88_rgb.Color:
    normalized = value.strip().removeprefix("#")
    if len(normalized) != 6:
        raise argparse.ArgumentTypeError("色はRRGGBB形式で指定してください")
    try:
        red = int(normalized[0:2], 16)
        green = int(normalized[2:4], 16)
        blue = int(normalized[4:6], 16)
    except ValueError as error:
        raise argparse.ArgumentTypeError("色は16進RRGGBB形式で指定してください") from error
    return red, green, blue


def rainbow_frame(phase: float) -> list[z88_rgb.Color]:
    colors: list[z88_rgb.Color] = []
    for slot in range(z88_rgb.RGB_SLOT_COUNT):
        hue = (slot / z88_rgb.RGB_SLOT_COUNT + phase) % 1.0
        red, green, blue = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
        colors.append((round(red * 255), round(green * 255), round(blue * 255)))
    return colors


def run_solid(controller: z88_rgb.Z88RGBController, color: z88_rgb.Color, seconds: float) -> None:
    controller.set_uniform(color)
    print(f"単色 #{color[0]:02X}{color[1]:02X}{color[2]:02X} を{seconds:g}秒表示します。")
    time.sleep(seconds)


def run_rainbow(controller: z88_rgb.Z88RGBController, seconds: float, fps: int) -> None:
    interval = 1.0 / fps
    started = time.monotonic()
    next_frame = started
    frame_index = 0
    while time.monotonic() - started < seconds:
        controller.send_frame(rainbow_frame(frame_index / (fps * 4)))
        frame_index += 1
        next_frame += interval
        time.sleep(max(0.0, next_frame - time.monotonic()))
    print(f"レインボーを{frame_index}フレーム表示しました。")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="E-YOOSO Z88 109のLEDを制御します。")
    subparsers = parser.add_subparsers(dest="mode", required=True)

    solid = subparsers.add_parser("solid", help="全スロットを同じ色で点灯します。")
    solid.add_argument("color", type=parse_color)
    solid.add_argument("--seconds", type=float, default=5.0)

    rainbow = subparsers.add_parser("rainbow", help="全スロットをレインボー表示します。")
    rainbow.add_argument("--seconds", type=float, default=5.0)
    rainbow.add_argument("--fps", type=int, default=30)
    return parser.parse_args(argv)


def validate_args(args: argparse.Namespace) -> None:
    if not 0.1 <= args.seconds <= 300:
        raise ValueError("表示秒数は0.1から300秒の範囲で指定してください")
    if args.mode == "rainbow" and not 1 <= args.fps <= 60:
        raise ValueError("FPSは1から60の範囲で指定してください")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        validate_args(args)
        import hid
        with z88_rgb.Z88RGBController(hid) as controller:
            try:
                if args.mode == "solid":
                    run_solid(controller, args.color, args.seconds)
                else:
                    run_rainbow(controller, args.seconds, args.fps)
            finally:
                controller.off()
        print("消灯しました。通常の内蔵発光モードへはFn+Mで戻せます。")
        return 0
    except Exception as error:
        print(f"RGB制御失敗: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
