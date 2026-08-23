"""Codex hook stdinを読み、Z88へ対応する状態色を送る。"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = REPOSITORY_ROOT / "logs" / "codex-led-hook.log"
sys.path.insert(0, str(REPOSITORY_ROOT))

from runtime_paths import activate_local_dependencies


activate_local_dependencies()


def log_error(error: Exception) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{timestamp} {type(error).__name__}: {error}\n")


def read_payload() -> dict[str, Any]:
    value = json.load(sys.stdin)
    if not isinstance(value, dict):
        raise ValueError("hook入力はJSONオブジェクトである必要があります")
    return value


def main() -> int:
    try:
        payload = read_payload()
        import hid
        from codex_led_status import apply_hook_status

        apply_hook_status(payload, hid)
    except Exception as error:
        # LED連携の故障でCodex本体の処理を止めない。詳細はローカルログへ残す。
        log_error(error)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
