import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import codex_hook_runtime


class HookPayloadTests(unittest.TestCase):
    def test_reads_complete_payload(self) -> None:
        payload = {"hook_event_name": "UserPromptSubmit", "prompt": "テスト"}

        self.assertEqual(
            codex_hook_runtime.parse_hook_payload(
                json.dumps(payload, ensure_ascii=False).encode("utf-8")
            ),
            payload,
        )

    def test_recovers_top_level_event_from_truncated_large_payload(self) -> None:
        raw_input = (
            b'{"session_id":"session","hook_event_name":"PostToolUse",'
            b'"tool_response":{"output":"' + (b"x" * 100_000)
        )

        payload = codex_hook_runtime.parse_hook_payload(raw_input)

        self.assertEqual(payload["hook_event_name"], "PostToolUse")
        self.assertTrue(payload[codex_hook_runtime.RECOVERED_INPUT_FIELD])

    def test_does_not_recover_nested_event_name(self) -> None:
        raw_input = b'{"tool_response":{"hook_event_name":"PermissionRequest"'

        with self.assertRaises(ValueError):
            codex_hook_runtime.parse_hook_payload(raw_input)


class InterProcessLockTests(unittest.TestCase):
    def test_serializes_separate_processes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            lock_path = Path(temporary_directory) / "hook.lock"
            with codex_hook_runtime.InterProcessFileLock(lock_path):
                result = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        (
                            "import sys; from pathlib import Path; "
                            "from codex_hook_runtime import InterProcessFileLock; "
                            "\ntry:\n with InterProcessFileLock("
                            "Path(sys.argv[1]), 0.05): pass"
                            "\nexcept TimeoutError:\n sys.exit(0)"
                            "\nsys.exit(1)"
                        ),
                        str(lock_path),
                    ],
                    cwd=Path(__file__).parents[1],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )

        self.assertEqual(result.returncode, 0, result.stderr)


class LEDUpdateDecisionTests(unittest.TestCase):
    def test_skips_redundant_blue_tool_updates(self) -> None:
        state = codex_hook_runtime.LEDRuntimeState(
            focused_session_id="session",
            displayed_color=(0, 102, 255),
            initialized=True,
            sessions={
                "session": codex_hook_runtime.SessionLEDState(
                    color=(0, 102, 255), focus_sequence=1
                )
            },
        )

        decision = codex_hook_runtime.decide_led_update(
            {
                "session_id": "session",
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "git status"},
            },
            state,
        )

        self.assertFalse(decision.send)

    def test_holds_yellow_until_the_approved_tool_finishes(self) -> None:
        tool_input = {"command": "python probe_device.py"}
        permission = {
            "session_id": "session",
            "hook_event_name": "PermissionRequest",
            "tool_name": "Bash",
            "tool_input": tool_input,
        }
        yellow = codex_hook_runtime.decide_led_update(
            permission,
            codex_hook_runtime.LEDRuntimeState(
                focused_session_id="session",
                initialized=True,
                sessions={"session": codex_hook_runtime.SessionLEDState()},
            ),
        )
        yellow_state = codex_hook_runtime.mark_update_succeeded(yellow)

        unrelated = codex_hook_runtime.decide_led_update(
            {
                "session_id": "session",
                "hook_event_name": "PostToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "git status"},
                "tool_response": {"exit_code": 0},
            },
            yellow_state,
        )
        approved = codex_hook_runtime.decide_led_update(
            {
                "session_id": "session",
                "hook_event_name": "PostToolUse",
                "tool_name": "Bash",
                "tool_input": tool_input,
                "tool_response": {"exit_code": 0},
            },
            yellow_state,
        )

        self.assertFalse(unrelated.send)
        self.assertEqual(
            unrelated.state.sessions["session"].color,
            (255, 170, 0),
        )
        self.assertTrue(approved.send)
        self.assertEqual(
            approved.state.sessions["session"].color,
            (0, 102, 255),
        )
        self.assertIsNone(
            approved.state.sessions["session"].pending_permission
        )

    def test_compaction_keeps_the_working_color_without_reinitializing(self) -> None:
        state = codex_hook_runtime.LEDRuntimeState(
            focused_session_id="session",
            displayed_color=(0, 102, 255),
            initialized=True,
            sessions={
                "session": codex_hook_runtime.SessionLEDState(
                    color=(0, 102, 255), focus_sequence=1
                )
            },
        )

        decision = codex_hook_runtime.decide_led_update(
            {
                "session_id": "session",
                "hook_event_name": "SessionStart",
                "source": "compact",
            },
            state,
        )

        self.assertEqual(
            decision.state.sessions["session"].color,
            (0, 102, 255),
        )
        self.assertFalse(decision.initialize)
        self.assertFalse(decision.send)

    def test_background_project_cannot_override_the_focused_project(self) -> None:
        state = codex_hook_runtime.LEDRuntimeState()
        for payload in (
            {
                "session_id": "background",
                "hook_event_name": "SessionStart",
                "source": "startup",
            },
            {
                "session_id": "background",
                "hook_event_name": "UserPromptSubmit",
            },
            {
                "session_id": "foreground",
                "hook_event_name": "SessionStart",
                "source": "startup",
            },
            {
                "session_id": "foreground",
                "hook_event_name": "UserPromptSubmit",
            },
            {
                "session_id": "foreground",
                "hook_event_name": "Stop",
            },
        ):
            decision = codex_hook_runtime.decide_led_update(payload, state)
            state = codex_hook_runtime.mark_update_succeeded(decision)

        background_failure = codex_hook_runtime.decide_led_update(
            {
                "session_id": "background",
                "hook_event_name": "PostToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "background command"},
                "tool_response": {"exit_code": 1},
            },
            state,
        )

        self.assertEqual(
            background_failure.state.focused_session_id,
            "foreground",
        )
        self.assertEqual(
            background_failure.state.sessions["background"].color,
            (255, 0, 0),
        )
        self.assertFalse(background_failure.send)

    def test_new_prompt_moves_focus_to_that_project(self) -> None:
        state = codex_hook_runtime.LEDRuntimeState(
            focused_session_id="foreground",
            displayed_color=(0, 255, 64),
            initialized=True,
            sessions={
                "foreground": codex_hook_runtime.SessionLEDState(
                    color=(0, 255, 64), focus_sequence=2
                ),
                "background": codex_hook_runtime.SessionLEDState(
                    color=(255, 0, 0), focus_sequence=1
                ),
            },
            sequence=2,
        )

        decision = codex_hook_runtime.decide_led_update(
            {
                "session_id": "background",
                "hook_event_name": "UserPromptSubmit",
            },
            state,
        )

        self.assertEqual(decision.state.focused_session_id, "background")
        self.assertEqual(
            decision.state.sessions["background"].color,
            (0, 102, 255),
        )
        self.assertTrue(decision.send)

    def test_ending_focused_project_restores_the_previous_project(self) -> None:
        state = codex_hook_runtime.LEDRuntimeState(
            focused_session_id="foreground",
            displayed_color=(0, 255, 64),
            initialized=True,
            sessions={
                "foreground": codex_hook_runtime.SessionLEDState(
                    color=(0, 255, 64), focus_sequence=2
                ),
                "background": codex_hook_runtime.SessionLEDState(
                    color=(0, 102, 255), focus_sequence=1
                ),
            },
            sequence=2,
        )

        decision = codex_hook_runtime.decide_led_update(
            {
                "session_id": "foreground",
                "hook_event_name": "SessionEnd",
            },
            state,
        )

        self.assertEqual(decision.state.focused_session_id, "background")
        self.assertNotIn("foreground", decision.state.sessions)
        self.assertTrue(decision.send)


if __name__ == "__main__":
    unittest.main()
