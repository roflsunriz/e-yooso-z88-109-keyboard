"""Codex lifecycle hookをZ88の状態色へ変換する。"""

from __future__ import annotations

from typing import Any

import z88_rgb


IDLE = (255, 255, 255)
WORKING = (0, 102, 255)
COMPLETED = (0, 255, 64)
WAITING = (255, 170, 0)
ERROR = (255, 0, 0)
UNASSIGNED = (0, 0, 0)

EVENT_COLORS: dict[str, z88_rgb.Color] = {
    "SessionStart": IDLE,
    "UserPromptSubmit": WORKING,
    "PermissionRequest": WAITING,
    "PreToolUse": WORKING,
    "PostToolUse": WORKING,
    "Stop": COMPLETED,
    "SessionEnd": UNASSIGNED,
    "SubagentStart": WORKING,
    "SubagentStop": WORKING,
}


def tool_failed(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("isError") is True or value.get("is_error") is True:
            return True
        exit_code = value.get("exit_code", value.get("exitCode"))
        if isinstance(exit_code, int) and exit_code != 0:
            return True
        status = value.get("status")
        if isinstance(status, str) and status.lower() in {"error", "failed", "failure"}:
            return True
        return any(tool_failed(child) for child in value.values())
    if isinstance(value, list):
        return any(tool_failed(child) for child in value)
    return False


def color_for_hook_payload(payload: dict[str, Any]) -> z88_rgb.Color | None:
    event_name = payload.get("hook_event_name")
    if not isinstance(event_name, str):
        return None
    if event_name == "PostToolUse" and tool_failed(payload.get("tool_response")):
        return ERROR
    return EVENT_COLORS.get(event_name)


def apply_hook_status(payload: dict[str, Any], hid_module: Any) -> bool:
    color = color_for_hook_payload(payload)
    if color is None:
        return False
    with z88_rgb.Z88RGBController(hid_module) as controller:
        initialize = payload.get("hook_event_name") not in {"PreToolUse", "PostToolUse"}
        controller.set_uniform(color, initialize=initialize)
    return True
