import unittest
from pathlib import Path

import install_codex_hooks


class HooksConfigTests(unittest.TestCase):
    def test_configures_required_lifecycle_events(self) -> None:
        repository_root = Path("C:/example/e-yooso-z88-109-keyboard")
        config = install_codex_hooks.build_user_hooks_config(
            repository_root=repository_root
        )

        self.assertEqual(
            set(config["hooks"]),
            {
                "SessionStart",
                "UserPromptSubmit",
                "PermissionRequest",
                "PreToolUse",
                "PostToolUse",
                "Stop",
                "SessionEnd",
            },
        )
        for groups in config["hooks"].values():
            for group in groups:
                for hook in group["hooks"]:
                    self.assertEqual(hook["type"], "command")
                    self.assertIn("commandWindows", hook)
                    self.assertIn(" -File ", hook["commandWindows"])
                    self.assertIn(
                        "run_codex_led_hook.ps1", hook["commandWindows"]
                    )
                    self.assertLessEqual(hook["timeout"], 3)

    def test_preserves_unrelated_user_hooks(self) -> None:
        existing = {
            "description": "既存設定",
            "hooks": {
                "Stop": [
                    {
                        "hooks": [
                            {"type": "command", "command": "python other_hook.py"}
                        ]
                    }
                ]
            },
        }

        config = install_codex_hooks.build_user_hooks_config(existing)

        self.assertEqual(config["description"], "既存設定")
        stop_handlers = [
            handler
            for group in config["hooks"]["Stop"]
            for handler in group["hooks"]
        ]
        self.assertTrue(
            any(
                handler.get("command") == "python other_hook.py"
                for handler in stop_handlers
            )
        )
        self.assertEqual(
            sum(
                install_codex_hooks.is_led_handler(handler)
                for handler in stop_handlers
            ),
            1,
        )

    def test_project_local_hooks_are_not_enabled(self) -> None:
        config_path = Path(__file__).parents[1] / ".codex" / "hooks.json"
        self.assertFalse(config_path.exists())

    def test_windows_wrapper_forwards_hook_stdin(self) -> None:
        wrapper_path = (
            Path(__file__).parents[1]
            / ".codex"
            / "hooks"
            / "run_codex_led_hook.ps1"
        )

        self.assertIn("$input | & python.exe", wrapper_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
