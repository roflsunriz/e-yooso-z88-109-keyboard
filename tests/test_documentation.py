import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).parents[1]


class DocumentationTests(unittest.TestCase):
    def test_agents_and_readme_include_verified_hardware_facts(self) -> None:
        for filename in ("AGENTS.md", "README.md"):
            text = (REPOSITORY_ROOT / filename).read_text(encoding="utf-8")
            with self.subTest(filename=filename):
                self.assertIn("Z88", text)
                self.assertIn("109", text)
                self.assertIn("258A:0049", text)
                self.assertIn("Col08", text)
                self.assertIn("382", text)
                self.assertIn("16ms", text)
                self.assertIn("3回", text)
                self.assertIn("Fn+M", text)

    def test_firmware_hash_is_consistent(self) -> None:
        expected_hash = (
            "0de319edb11a4a532bf27cc263a6491b4a98e666a627b0df6cd51a547f9fabe8"
        )
        for filename in ("AGENTS.md", "README.md", "docs/protocol-notes.md"):
            text = (REPOSITORY_ROOT / filename).read_text(encoding="utf-8")
            with self.subTest(filename=filename):
                self.assertIn(expected_hash, text)

    def test_codex_hook_states_are_documented(self) -> None:
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        for event_name in (
            "SessionStart",
            "UserPromptSubmit",
            "PreToolUse",
            "PostToolUse",
            "PermissionRequest",
            "Stop",
            "SessionEnd",
        ):
            with self.subTest(event_name=event_name):
                self.assertIn(event_name, readme)

    def test_outdated_report8_incompatibility_claim_is_absent(self) -> None:
        combined = "\n".join(
            (REPOSITORY_ROOT / filename).read_text(encoding="utf-8")
            for filename in (
                "AGENTS.md",
                "README.md",
                "CHANGELOG.md",
                "how-to-update.md",
                "docs/protocol-notes.md",
            )
        )
        self.assertNotIn("Report 8直接RGB方式は本機では非互換", combined)


if __name__ == "__main__":
    unittest.main()
