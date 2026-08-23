import unittest

import backup_firmware


class DescriptorTests(unittest.TestCase):
    def test_extracts_report_ids_from_real_z88_descriptors(self) -> None:
        report5 = bytes.fromhex(
            "06 00 FF 09 01 A1 01 85 05 19 01 29 02 15 00 26 FF 00 75 08 95 05 B1 02 C0"
        )
        report6 = bytes.fromhex(
            "06 00 FF 09 01 A1 01 85 06 19 01 29 02 15 00 26 FF 00 75 08 96 07 04 B1 02 C0"
        )

        self.assertEqual(backup_firmware.report_ids_from_descriptor(report5), {5})
        self.assertEqual(backup_firmware.report_ids_from_descriptor(report6), {6})

    def test_rejects_truncated_descriptor(self) -> None:
        with self.assertRaisesRegex(ValueError, "途中"):
            backup_firmware.report_ids_from_descriptor(bytes((0x85,)))


if __name__ == "__main__":
    unittest.main()
