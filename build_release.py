"""GitHub Release向けの再現可能なZIPとリリースノートを生成する。"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import zipfile
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path


PROJECT_NAME = "e-yooso-z88-109-keyboard"
TAG_PATTERN = re.compile(
    r"^v(?P<version>(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*))$"
)
RELEASE_HEADER_PATTERN = re.compile(
    r"^## \[(?P<version>\d+\.\d+\.\d+)\] - (?P<date>\d{4}-\d{2}-\d{2})$",
    re.MULTILINE,
)
LINK_DEFINITION_PATTERN = re.compile(r"^\[[^\]]+\]:\s", re.MULTILINE)
RELEASE_METADATA = {
    "CHANGELOG.md",
    "README.md",
    "how-to-update.md",
    "requirements.txt",
}
REQUIRED_RELEASE_PATHS = RELEASE_METADATA | {
    ".codex/hooks/codex_led_hook.py",
    "LICENSE",
    "analyze_firmware.py",
    "backup_firmware.py",
    "codex_hook_runtime.py",
    "codex_led_status.py",
    "direct_rgb_probe.py",
    "docs/protocol-notes.md",
    "install_codex_hooks.py",
    "isp_protocol.py",
    "probe_device.py",
    "rgb_cli.py",
    "runtime_paths.py",
    "z88_rgb.py",
}


def version_from_tag(tag: str) -> str:
    match = TAG_PATTERN.fullmatch(tag)
    if match is None:
        raise ValueError(f"リリースタグはvMAJOR.MINOR.PATCH形式にしてください: {tag}")
    return match.group("version")


def extract_release_notes(changelog: str, version: str) -> str:
    matches = list(RELEASE_HEADER_PATTERN.finditer(changelog))
    release_match = next(
        (match for match in matches if match.group("version") == version),
        None,
    )
    if release_match is None:
        raise ValueError(f"CHANGELOG.mdにリリース {version} がありません")

    next_match = next(
        (match for match in matches if match.start() > release_match.start()),
        None,
    )
    link_definition = LINK_DEFINITION_PATTERN.search(
        changelog,
        release_match.end(),
    )
    end_candidates = [len(changelog)]
    if next_match is not None:
        end_candidates.append(next_match.start())
    if link_definition is not None:
        end_candidates.append(link_definition.start())
    end = min(end_candidates)
    notes = changelog[release_match.end() : end].strip()
    if not notes:
        raise ValueError(f"CHANGELOG.mdのリリース {version} が空です")
    return notes + "\n"


def select_release_files(tracked_paths: Iterable[str]) -> list[str]:
    normalized_paths = {path.replace("\\", "/") for path in tracked_paths}
    selected = sorted(
        path
        for path in normalized_paths
        if path in RELEASE_METADATA
        or path == ".codex/hooks/codex_led_hook.py"
        or ("/" not in path and path.endswith(".py"))
        or (path.startswith("docs/") and path.endswith(".md"))
        or path == "LICENSE"
    )
    missing = sorted(REQUIRED_RELEASE_PATHS - set(selected))
    if missing:
        raise ValueError(
            "リリースに必要なファイルがGit管理されていません: "
            + ", ".join(missing)
        )
    return selected


def git_output(repository_root: Path, *arguments: str) -> bytes:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository_root,
        check=True,
        stdout=subprocess.PIPE,
    )
    return result.stdout


def tracked_files(repository_root: Path, reference: str) -> list[str]:
    output = git_output(
        repository_root,
        "ls-tree",
        "-r",
        "--name-only",
        "-z",
        reference,
    )
    return [path for path in output.decode("utf-8").split("\0") if path]


def commit_timestamp(repository_root: Path, reference: str) -> int:
    return int(
        git_output(
            repository_root,
            "log",
            "-1",
            "--format=%ct",
            reference,
        ).strip()
    )


def release_contents(
    repository_root: Path,
    reference: str,
    release_paths: Sequence[str],
) -> dict[str, bytes]:
    return {
        path: git_output(repository_root, "show", f"{reference}:{path}")
        for path in release_paths
    }


def zip_timestamp(timestamp: int) -> tuple[int, int, int, int, int, int]:
    value = datetime.fromtimestamp(timestamp, timezone.utc)
    if value.year < 1980:
        return (1980, 1, 1, 0, 0, 0)
    return (value.year, value.month, value.day, value.hour, value.minute, value.second)


def write_release_archive(
    archive_path: Path,
    contents: Mapping[str, bytes],
    archive_root: str,
    timestamp: int,
) -> None:
    temporary_path = archive_path.with_suffix(archive_path.suffix + ".tmp")
    temporary_path.unlink(missing_ok=True)
    date_time = zip_timestamp(timestamp)
    try:
        with zipfile.ZipFile(
            temporary_path,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for relative_path, content in contents.items():
                member = zipfile.ZipInfo(
                    f"{archive_root}/{relative_path}",
                    date_time=date_time,
                )
                member.compress_type = zipfile.ZIP_DEFLATED
                member.create_system = 3
                member.external_attr = 0o100644 << 16
                archive.writestr(member, content)
        temporary_path.replace(archive_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def write_checksum(archive_path: Path, checksum_path: Path) -> None:
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    checksum_path.write_text(
        f"{digest}  {archive_path.name}\n",
        encoding="ascii",
    )


def build_release(
    repository_root: Path,
    output_directory: Path,
    tag: str,
    reference: str,
) -> None:
    version = version_from_tag(tag)
    notes = extract_release_notes(
        git_output(repository_root, "show", f"{reference}:CHANGELOG.md").decode(
            "utf-8"
        ),
        version,
    )
    release_paths = select_release_files(tracked_files(repository_root, reference))
    contents = release_contents(repository_root, reference, release_paths)
    output_directory.mkdir(parents=True, exist_ok=True)

    archive_root = f"{PROJECT_NAME}-{tag}"
    archive_path = output_directory / f"{archive_root}.zip"
    checksum_path = output_directory / f"{archive_path.name}.sha256"
    notes_path = output_directory / f"release-notes-{version}.md"

    write_release_archive(
        archive_path,
        contents,
        archive_root,
        commit_timestamp(repository_root, reference),
    )
    write_checksum(archive_path, checksum_path)
    notes_path.write_text(notes, encoding="utf-8")

    print(f"archive={archive_path}")
    print(f"checksum={checksum_path}")
    print(f"notes={notes_path}")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, help="vMAJOR.MINOR.PATCH形式のタグ")
    parser.add_argument(
        "--ref",
        default="HEAD",
        help="成果物へ格納するGit参照（既定値: HEAD）",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dist"),
        help="成果物の出力先（既定値: dist）",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    build_release(
        Path(__file__).resolve().parent,
        args.output_dir.resolve(),
        args.tag,
        args.ref,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
