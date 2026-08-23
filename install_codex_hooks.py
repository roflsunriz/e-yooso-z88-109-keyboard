"""Z88 LED連携をCodexのユーザー共通Hooksへ登録する。"""

from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parent
DEFAULT_HOOKS_PATH = Path.home() / ".codex" / "hooks.json"
DESCRIPTION = "E-YOOSO Z88 109へCodexのライフサイクル状態を表示します。"
EVENT_MATCHERS: dict[str, str | None] = {
    "SessionStart": None,
    "UserPromptSubmit": None,
    "PermissionRequest": ".*",
    "PreToolUse": ".*",
    "PostToolUse": ".*",
    "Stop": None,
    "SessionEnd": None,
}
LED_HANDLER_MARKERS = ("codex_led_hook.py", "run_codex_led_hook.ps1")


def build_handler(repository_root: Path) -> dict[str, Any]:
    hook_script = (
        repository_root / ".codex" / "hooks" / "codex_led_hook.py"
    ).resolve()
    windows_wrapper = (
        repository_root / ".codex" / "hooks" / "run_codex_led_hook.ps1"
    ).resolve()
    return {
        "type": "command",
        "command": f'python3 "{hook_script.as_posix()}"',
        "commandWindows": (
            "powershell.exe -NoProfile -ExecutionPolicy Bypass "
            f'-File "{windows_wrapper}"'
        ),
        "timeout": 3,
    }


def is_led_handler(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    commands = (value.get("command"), value.get("commandWindows"))
    return any(
        isinstance(command, str) and marker in command
        for command in commands
        for marker in LED_HANDLER_MARKERS
    )


def remove_existing_led_groups(groups: Any) -> list[dict[str, Any]]:
    if not isinstance(groups, list):
        raise ValueError("Hooksのイベント設定は配列である必要があります")

    remaining: list[dict[str, Any]] = []
    for group in groups:
        if not isinstance(group, dict):
            raise ValueError("Hooksのmatcherグループはオブジェクトである必要があります")
        handlers = group.get("hooks")
        if not isinstance(handlers, list):
            raise ValueError("Hooksのハンドラー設定は配列である必要があります")
        kept_handlers = [
            handler for handler in handlers if not is_led_handler(handler)
        ]
        if kept_handlers:
            kept_group = copy.deepcopy(group)
            kept_group["hooks"] = kept_handlers
            remaining.append(kept_group)
    return remaining


def build_user_hooks_config(
    existing: dict[str, Any] | None = None,
    repository_root: Path = REPOSITORY_ROOT,
) -> dict[str, Any]:
    config = copy.deepcopy(existing) if existing is not None else {}
    if not isinstance(config, dict):
        raise ValueError("hooks.jsonのルートはJSONオブジェクトである必要があります")

    hooks = config.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("hooks.jsonのhooksはJSONオブジェクトである必要があります")

    handler = build_handler(repository_root)
    for event_name, matcher in EVENT_MATCHERS.items():
        current_groups = remove_existing_led_groups(hooks.get(event_name, []))
        new_group: dict[str, Any] = {"hooks": [copy.deepcopy(handler)]}
        if matcher is not None:
            new_group["matcher"] = matcher
        hooks[event_name] = [*current_groups, new_group]

    config.setdefault("description", DESCRIPTION)
    return config


def load_existing_config(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("既存のhooks.jsonはJSONオブジェクトである必要があります")
    return value


def write_config(path: Path, config: dict[str, Any]) -> Path | None:
    path.parent.mkdir(parents=True, exist_ok=True)
    backup_path: Path | None = None
    if path.exists():
        timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S-%f")
        backup_path = path.with_name(f"{path.name}.bak-{timestamp}")
        shutil.copy2(path, backup_path)

    temporary_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)
    return backup_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Z88 LED連携を全プロジェクト共通のCodex Hooksへ登録します。"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ユーザー設定を書き換えず、生成するJSONだけを表示します。",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = build_user_hooks_config(load_existing_config(DEFAULT_HOOKS_PATH))
    if args.dry_run:
        print(json.dumps(config, ensure_ascii=False, indent=2))
        return 0

    backup_path = write_config(DEFAULT_HOOKS_PATH, config)
    print(f"ユーザー共通Hooksを更新しました: {DEFAULT_HOOKS_PATH}")
    if backup_path is not None:
        print(f"更新前の設定を退避しました: {backup_path}")
    print(
        "Codexで新しいフック定義を確認して信頼し、"
        "新しいタスクで動作確認してください。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
