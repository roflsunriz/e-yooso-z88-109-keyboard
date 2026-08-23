import json
import unittest
from pathlib import Path


class HooksConfigTests(unittest.TestCase):
    def test_configures_required_lifecycle_events(self) -> None:
        config_path = Path(__file__).parents[1] / ".codex" / "hooks.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))

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
                    self.assertLessEqual(hook["timeout"], 3)

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
