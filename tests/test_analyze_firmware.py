import unittest

import analyze_firmware


class IntelHexTests(unittest.TestCase):
    def test_parses_data_and_eof_records(self) -> None:
        parsed = analyze_firmware.parse_intel_hex(
            ":040000000200660292\n:00000001FF\n"
        )

        self.assertEqual(parsed, bytes((0x02, 0x00, 0x66, 0x02)))

    def test_rejects_bad_checksum(self) -> None:
        with self.assertRaisesRegex(ValueError, "チェックサム"):
            analyze_firmware.parse_intel_hex(
                ":040000000200660293\n:00000001FF\n"
            )


class EqualRunsTests(unittest.TestCase):
    def test_reports_only_long_enough_runs(self) -> None:
        self.assertEqual(
            analyze_firmware.equal_runs(b"XXabcdefghYY", b"ZZabcdefghWW", 8),
            [(2, 8)],
        )


if __name__ == "__main__":
    unittest.main()
