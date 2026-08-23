"""Codex hook stdinを読み、Z88へ対応する状態色を送る。"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = REPOSITORY_ROOT / "logs" / "codex-led-hook.log"
LOCK_PATH = REPOSITORY_ROOT / "logs" / "codex-led-hook.lock"
STATE_PATH = REPOSITORY_ROOT / "logs" / "codex-led-hook-state.json"
sys.path.insert(0, str(REPOSITORY_ROOT))

from codex_hook_runtime import (
    InterProcessFileLock,
    decide_led_update,
    load_runtime_state,
    mark_update_succeeded,
    parse_hook_payload,
    save_runtime_state,
)
from runtime_paths import activate_local_dependencies


activate_local_dependencies()


def log_error(error: Exception) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{timestamp} {type(error).__name__}: {error}\n")


def read_payload() -> dict[str, object]:
    return parse_hook_payload(sys.stdin.buffer.read())


def main() -> int:
    try:
        payload = read_payload()
        with InterProcessFileLock(LOCK_PATH):
            state = load_runtime_state(STATE_PATH)
            decision = decide_led_update(payload, state)
            if not decision.send:
                save_runtime_state(STATE_PATH, decision.state)
                return 0

            import hid
            from codex_led_status import apply_hook_status

            try:
                apply_hook_status(
                    payload,
                    hid,
                    initialize=decision.initialize,
                )
                initialized = True
            except (OSError, RuntimeError):
                if decision.initialize:
                    raise
                time.sleep(0.05)
                apply_hook_status(payload, hid, initialize=True)
                initialized = True
            save_runtime_state(
                STATE_PATH,
                mark_update_succeeded(decision, initialized=initialized),
            )
    except Exception as error:
        # LED連携の故障でCodex本体の処理を止めない。詳細はローカルログへ残す。
        log_error(error)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
