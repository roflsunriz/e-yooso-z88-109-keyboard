import unittest

import codex_led_status


class CodexLEDStatusTests(unittest.TestCase):
    def test_maps_official_status_palette_to_hook_events(self) -> None:
        expected = {
            "SessionStart": (255, 255, 255),
            "UserPromptSubmit": (0, 102, 255),
            "PermissionRequest": (255, 170, 0),
            "PreToolUse": (0, 102, 255),
            "PostToolUse": (0, 102, 255),
            "Stop": (0, 255, 64),
            "SessionEnd": (0, 0, 0),
        }
        for event_name, color in expected.items():
            with self.subTest(event_name=event_name):
                self.assertEqual(
                    codex_led_status.color_for_hook_payload(
                        {"hook_event_name": event_name}
                    ),
                    color,
                )

    def test_ignores_unknown_or_missing_event(self) -> None:
        self.assertIsNone(codex_led_status.color_for_hook_payload({}))
        self.assertIsNone(
            codex_led_status.color_for_hook_payload(
                {"hook_event_name": "UnknownEvent"}
            )
        )

    def test_keeps_working_color_during_compaction(self) -> None:
        self.assertEqual(
            codex_led_status.color_for_hook_payload(
                {"hook_event_name": "SessionStart", "source": "compact"}
            ),
            (0, 102, 255),
        )

    def test_maps_failed_tool_response_to_red(self) -> None:
        failure_responses = (
            {"exit_code": 1},
            {"isError": True},
            {"nested": {"status": "failed"}},
        )
        for tool_response in failure_responses:
            with self.subTest(tool_response=tool_response):
                self.assertEqual(
                    codex_led_status.color_for_hook_payload(
                        {
                            "hook_event_name": "PostToolUse",
                            "tool_response": tool_response,
                        }
                    ),
                    (255, 0, 0),
                )

    def test_keeps_successful_tool_response_blue(self) -> None:
        self.assertEqual(
            codex_led_status.color_for_hook_payload(
                {
                    "hook_event_name": "PostToolUse",
                    "tool_response": {"exit_code": 0, "status": "completed"},
                }
            ),
            (0, 102, 255),
        )


if __name__ == "__main__":
    unittest.main()
