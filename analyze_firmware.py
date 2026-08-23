"""Z88ファームウェアの識別情報と同系統ダンプとの差分を解析する。"""

from __future__ import annotations

import argparse
import hashlib
import re
from collections.abc import Sequence
from pathlib import Path


def parse_intel_hex(text: str) -> bytes:
    memory: dict[int, int] = {}
    base_address = 0
    eof_seen = False

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if not line.startswith(":"):
            raise ValueError(f"{line_number}行目がIntel HEXレコードではありません")
        try:
            record = bytes.fromhex(line[1:])
        except ValueError as error:
            raise ValueError(f"{line_number}行目の16進表記が不正です") from error
        if len(record) < 5 or len(record) != record[0] + 5:
            raise ValueError(f"{line_number}行目のレコード長が不正です")
        if sum(record) & 0xFF:
            raise ValueError(f"{line_number}行目のチェックサムが不正です")

        length = record[0]
        address = (record[1] << 8) | record[2]
        record_type = record[3]
        data = record[4 : 4 + length]
        if record_type == 0x00:
            for offset, value in enumerate(data):
                memory[base_address + address + offset] = value
        elif record_type == 0x01:
            eof_seen = True
            break
        elif record_type == 0x02:
            if len(data) != 2:
                raise ValueError(f"{line_number}行目の拡張セグメントアドレスが不正です")
            base_address = int.from_bytes(data, "big") << 4
        elif record_type == 0x04:
            if len(data) != 2:
                raise ValueError(f"{line_number}行目の拡張リニアアドレスが不正です")
            base_address = int.from_bytes(data, "big") << 16
        elif record_type not in (0x03, 0x05):
            raise ValueError(f"{line_number}行目の未対応レコード種別: {record_type}")

    if not eof_seen:
        raise ValueError("Intel HEXのEOFレコードがありません")
    if not memory:
        return b""
    highest_address = max(memory)
    output = bytearray([0xFF]) * (highest_address + 1)
    for address, value in memory.items():
        output[address] = value
    return bytes(output)


def ascii_strings(data: bytes, minimum_length: int = 5) -> list[tuple[int, str]]:
    pattern = re.compile(rb"[ -~]{%d,}" % minimum_length)
    return [
        (match.start(), match.group().decode("ascii", errors="replace"))
        for match in pattern.finditer(data)
    ]


def equal_runs(left: bytes, right: bytes, minimum_length: int = 32) -> list[tuple[int, int]]:
    limit = min(len(left), len(right))
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for offset in range(limit + 1):
        equal = offset < limit and left[offset] == right[offset]
        if equal and start is None:
            start = offset
        elif not equal and start is not None:
            if offset - start >= minimum_length:
                runs.append((start, offset - start))
            start = None
    return runs


def summarize(name: str, data: bytes) -> None:
    print(
        f"{name}: size={len(data)} "
        f"sha256={hashlib.sha256(data).hexdigest()}"
    )
    for offset, value in ascii_strings(data):
        if "CK " in value or "Gaming" in value or "Keyboard" in value:
            print(f"  string @0x{offset:04X}: {value}")
    for pattern_name, pattern in (
        ("VID/PID 258A:0049", bytes.fromhex("8A 25 49 00")),
        ("Report 8 header", bytes.fromhex("08 0A 7A 01")),
    ):
        offsets = [
            offset for offset in range(len(data)) if data.startswith(pattern, offset)
        ]
        print(f"  {pattern_name}: {[f'0x{offset:04X}' for offset in offsets]}")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="8051キーボードファームを比較します。")
    parser.add_argument("firmware", type=Path)
    parser.add_argument("--reference-ihex", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    firmware = args.firmware.read_bytes()
    summarize("firmware", firmware)

    if args.reference_ihex is None:
        return 0
    reference = parse_intel_hex(args.reference_ihex.read_text(encoding="ascii"))
    summarize("reference", reference)
    limit = min(len(firmware), len(reference))
    equal_count = sum(
        firmware[offset] == reference[offset] for offset in range(limit)
    )
    print(
        f"same-offset bytes: {equal_count}/{limit} "
        f"({equal_count / limit:.2%})"
    )
    runs = sorted(equal_runs(firmware, reference), key=lambda item: item[1], reverse=True)
    print("longest equal runs:")
    for offset, length in runs[:20]:
        print(f"  0x{offset:04X}-0x{offset + length - 1:04X}: {length} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
