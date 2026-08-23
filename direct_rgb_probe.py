"""BYK916動画モード初期化後のReport 8直接RGBを実機確認する。"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from probe_device import path_text
from runtime_paths import activate_local_dependencies
from z88_rgb import PACKET_LENGTH, Z88RGBController, find_report8_device


activate_local_dependencies()


def run_probe(hid_module: Any, duration_seconds: float) -> None:
    info = find_report8_device(hid_module)
    with Z88RGBController(hid_module) as controller:
        try:
            controller.initialize_video_mode()
            print("動画モード初期化パケットを3回送信しました。")
            controller.set_uniform((255, 0, 0))
            print(f"最大赤を送信しました。{duration_seconds:g}秒待機します。")
            import time
            time.sleep(duration_seconds)
        finally:
            controller.off()
            print("消灯パケットを送信しました。通常モードへはFn+Mで戻せます。")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Z88のBYK916動画モードを確認します。")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="ゼロパケット3回の後に最大赤を5秒送信します。",
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
        info = find_report8_device(hid)
        print(f"対象確認: {path_text(info['path'])}, report_length={PACKET_LENGTH}")
        if not args.apply:
            print("dry-run完了。Report 8は送信していません。")
            return 0
        run_probe(hid, 5.0)
        return 0
    except Exception as error:
        print(f"直接RGB診断失敗: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
