import hashlib
import tempfile
import unittest
import zipfile
from pathlib import Path

import build_release


class ReleaseMetadataTests(unittest.TestCase):
    def test_accepts_semantic_version_tag(self) -> None:
        self.assertEqual(build_release.version_from_tag("v1.2.3"), "1.2.3")

    def test_rejects_non_release_tags(self) -> None:
        for tag in ("1.2.3", "v1.2", "v01.2.3", "v1.2.3-rc.1"):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                build_release.version_from_tag(tag)

    def test_extracts_only_requested_changelog_section(self) -> None:
        changelog = """# 変更履歴

## [Unreleased]

## [1.1.0] - 2026-08-25

### Added

- 次の変更。

## [1.0.0] - 2026-08-24

### Added

- 最初の変更。

[1.0.0]: https://example.invalid/v1.0.0
"""

        self.assertEqual(
            build_release.extract_release_notes(changelog, "1.0.0"),
            "### Added\n\n- 最初の変更。\n",
        )

    def test_selects_runtime_files_without_development_configuration(self) -> None:
        tracked = build_release.REQUIRED_RELEASE_PATHS | {
            "build_release.py",
            ".github/workflows/release.yml",
            "AGENTS.md",
            "tests/test_build_release.py",
        }

        selected = build_release.select_release_files(tracked)

        self.assertIn("build_release.py", selected)
        self.assertIn("LICENSE", selected)
        self.assertIn("docs/protocol-notes.md", selected)
        self.assertNotIn(".github/workflows/release.yml", selected)
        self.assertNotIn("AGENTS.md", selected)
        self.assertNotIn("tests/test_build_release.py", selected)


class ReleaseArchiveTests(unittest.TestCase):
    def test_writes_reproducible_archive_and_matching_checksum(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "README.md").write_text("説明\n", encoding="utf-8")
            (root / "app.py").write_text("print('ok')\n", encoding="utf-8")
            first = root / "first.zip"
            second = root / "second.zip"
            paths = ["README.md", "app.py"]

            for archive_path in (first, second):
                build_release.write_release_archive(
                    root,
                    archive_path,
                    paths,
                    "project-v1.0.0",
                    timestamp=1_700_000_000,
                )

            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                self.assertEqual(
                    archive.namelist(),
                    [
                        "project-v1.0.0/README.md",
                        "project-v1.0.0/app.py",
                    ],
                )

            checksum = root / "first.zip.sha256"
            build_release.write_checksum(first, checksum)
            expected = hashlib.sha256(first.read_bytes()).hexdigest()
            self.assertEqual(
                checksum.read_text(encoding="ascii"),
                f"{expected}  first.zip\n",
            )


if __name__ == "__main__":
    unittest.main()
