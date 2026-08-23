"""Codex LED hookの入力復旧、状態抑制、プロセス間排他を担う。"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, BinaryIO

from codex_led_status import color_for_hook_payload
from z88_rgb import Color


RECOVERED_INPUT_FIELD = "_codex_led_recovered_input"


def _extract_top_level_event_name(text: str) -> str | None:
    """途中で切れたJSONから、完成済みのトップレベルイベント名だけを読む。"""

    decoder = json.JSONDecoder()
    index = 0
    length = len(text)

    while index < length and text[index].isspace():
        index += 1
    if index >= length or text[index] != "{":
        return None
    index += 1

    while index < length:
        while index < length and text[index].isspace():
            index += 1
        if index >= length or text[index] == "}":
            return None
        try:
            key, index = decoder.raw_decode(text, index)
        except json.JSONDecodeError:
            return None
        if not isinstance(key, str):
            return None

        while index < length and text[index].isspace():
            index += 1
        if index >= length or text[index] != ":":
            return None
        index += 1
        while index < length and text[index].isspace():
            index += 1

        try:
            value, index = decoder.raw_decode(text, index)
        except json.JSONDecodeError:
            return None
        if key == "hook_event_name":
            return value if isinstance(value, str) else None

        while index < length and text[index].isspace():
            index += 1
        if index >= length or text[index] != ",":
            return None
        index += 1

    return None


def parse_hook_payload(raw_input: bytes) -> dict[str, Any]:
    """stdin JSONを読み、大容量入力の末尾欠落時はイベント名だけ復旧する。"""

    try:
        text = raw_input.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("hook入力がUTF-8ではありません") from error

    try:
        value = json.loads(text)
    except json.JSONDecodeError as error:
        event_name = _extract_top_level_event_name(text)
        if event_name is None:
            raise ValueError("hook入力のJSONを復旧できません") from error
        return {
            "hook_event_name": event_name,
            RECOVERED_INPUT_FIELD: True,
        }

    if not isinstance(value, dict):
        raise ValueError("hook入力はJSONオブジェクトである必要があります")
    return value


class InterProcessFileLock:
    """標準ライブラリだけで同一ロックファイルへの処理を直列化する。"""

    def __init__(self, path: Path, timeout: float = 2.0) -> None:
        self._path = path
        self._timeout = timeout
        self._file: BinaryIO | None = None

    def __enter__(self) -> "InterProcessFileLock":
        self._path.parent.mkdir(parents=True, exist_ok=True)
        lock_file = self._path.open("a+b")
        if lock_file.seek(0, os.SEEK_END) == 0:
            lock_file.write(b"\0")
            lock_file.flush()

        deadline = time.monotonic() + self._timeout
        while True:
            try:
                lock_file.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._file = lock_file
                return self
            except OSError as error:
                if time.monotonic() >= deadline:
                    lock_file.close()
                    raise TimeoutError("LEDフックの排他待機がタイムアウトしました") from error
                time.sleep(0.01)

    def __exit__(self, *_exc_info: object) -> None:
        if self._file is None:
            return
        self._file.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
        self._file.close()
        self._file = None


@dataclass(frozen=True)
class SessionLEDState:
    color: Color | None = None
    pending_permission: str | None = None
    focus_sequence: int = 0


@dataclass(frozen=True)
class LEDRuntimeState:
    focused_session_id: str | None = None
    displayed_color: Color | None = None
    initialized: bool = False
    sequence: int = 0
    sessions: dict[str, SessionLEDState] | None = None


@dataclass(frozen=True)
class LEDUpdateDecision:
    state: LEDRuntimeState
    send: bool
    initialize: bool


def load_runtime_state(path: Path) -> LEDRuntimeState:
    if not path.exists():
        return LEDRuntimeState()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        sessions: dict[str, SessionLEDState] = {}
        for session_id, session_value in value.get("sessions", {}).items():
            if not isinstance(session_id, str) or not isinstance(session_value, dict):
                raise ValueError("保存セッションが不正です")
            sessions[session_id] = SessionLEDState(
                color=_load_color(session_value.get("color")),
                pending_permission=session_value.get("pending_permission"),
                focus_sequence=int(session_value.get("focus_sequence", 0)),
            )
        return LEDRuntimeState(
            focused_session_id=value.get("focused_session_id"),
            displayed_color=_load_color(value.get("displayed_color")),
            initialized=value.get("initialized") is True,
            sequence=int(value.get("sequence", 0)),
            sessions=sessions,
        )
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return LEDRuntimeState()


def save_runtime_state(path: Path, state: LEDRuntimeState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary_path.write_text(
        json.dumps(
            {
                "version": 2,
                "focused_session_id": state.focused_session_id,
                "displayed_color": state.displayed_color,
                "initialized": state.initialized,
                "sequence": state.sequence,
                "sessions": {
                    session_id: {
                        "color": session.color,
                        "pending_permission": session.pending_permission,
                        "focus_sequence": session.focus_sequence,
                    }
                    for session_id, session in (state.sessions or {}).items()
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    temporary_path.replace(path)


def _load_color(value: Any) -> Color | None:
    if value is None:
        return None
    color = tuple(value)
    if len(color) != 3 or not all(isinstance(part, int) for part in color):
        raise ValueError("保存色が不正です")
    return color


def _tool_fingerprint(payload: dict[str, Any]) -> str | None:
    tool_name = payload.get("tool_name")
    if not isinstance(tool_name, str):
        return None
    encoded = json.dumps(
        {"tool_name": tool_name, "tool_input": payload.get("tool_input")},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def decide_led_update(
    payload: dict[str, Any], state: LEDRuntimeState
) -> LEDUpdateDecision:
    event_name = payload.get("hook_event_name")
    if not isinstance(event_name, str):
        return LEDUpdateDecision(state, send=False, initialize=False)

    sessions = dict(state.sessions or {})
    session_id = payload.get("session_id")
    if not isinstance(session_id, str):
        session_id = state.focused_session_id
    if session_id is None:
        return LEDUpdateDecision(state, send=False, initialize=False)

    color = color_for_hook_payload(payload)
    if color is None:
        return LEDUpdateDecision(state, send=False, initialize=False)

    session = sessions.get(session_id, SessionLEDState())
    pending_permission = session.pending_permission
    fingerprint = _tool_fingerprint(payload)
    if event_name == "PermissionRequest":
        pending_permission = fingerprint or "unknown"
    elif pending_permission is not None and event_name in {"PreToolUse", "PostToolUse"}:
        if event_name != "PostToolUse" or fingerprint != pending_permission:
            return LEDUpdateDecision(state, send=False, initialize=False)
        pending_permission = None
    elif event_name in {"UserPromptSubmit", "Stop", "SessionEnd"}:
        pending_permission = None

    sequence = state.sequence + 1
    focused_session_id = state.focused_session_id
    focus_sequence = session.focus_sequence
    if event_name == "UserPromptSubmit" or (
        event_name == "SessionStart" and payload.get("source") != "compact"
    ):
        focused_session_id = session_id
        focus_sequence = sequence

    if event_name == "SessionEnd":
        sessions.pop(session_id, None)
        if focused_session_id == session_id:
            focused_session_id = max(
                sessions,
                key=lambda candidate: sessions[candidate].focus_sequence,
                default=None,
            )
    else:
        sessions[session_id] = SessionLEDState(
            color=color,
            pending_permission=pending_permission,
            focus_sequence=focus_sequence,
        )

    if focused_session_id is None:
        target_color = (0, 0, 0)
    else:
        focused_session = sessions.get(focused_session_id)
        target_color = focused_session.color if focused_session is not None else None

    force_initialization = (
        event_name == "SessionStart"
        and payload.get("source") != "compact"
        and focused_session_id == session_id
    )
    initialize = force_initialization or not state.initialized
    send = target_color is not None and (
        initialize or target_color != state.displayed_color
    )
    next_state = LEDRuntimeState(
        focused_session_id=focused_session_id,
        displayed_color=state.displayed_color,
        initialized=state.initialized,
        sequence=sequence,
        sessions=sessions,
    )
    return LEDUpdateDecision(next_state, send=send, initialize=initialize)


def mark_update_succeeded(
    decision: LEDUpdateDecision, *, initialized: bool = True
) -> LEDRuntimeState:
    focused_session = (decision.state.sessions or {}).get(
        decision.state.focused_session_id or ""
    )
    displayed_color = (
        focused_session.color if focused_session is not None else (0, 0, 0)
    )
    if displayed_color == (0, 0, 0):
        initialized = False
    return replace(
        decision.state,
        displayed_color=displayed_color,
        initialized=initialized,
    )
