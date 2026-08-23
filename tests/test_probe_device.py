import unittest

import probe_device


class ProbeDeviceTests(unittest.TestCase):
    def test_converts_byte_path(self) -> None:
        self.assertEqual(probe_device.path_text(b"device&Col05"), "device&Col05")

    def test_finds_collection_case_insensitively(self) -> None:
        col05 = {"path": b"device&Col05"}

        selected = probe_device.find_collection(
            [{"path": b"device&Col03"}, col05], "col05"
        )

        self.assertIs(selected, col05)

    def test_rejects_missing_or_ambiguous_collection(self) -> None:
        col05 = {"path": b"device&Col05"}
        for devices in ([], [col05, col05.copy()]):
            with self.subTest(device_count=len(devices)), self.assertRaises(RuntimeError):
                probe_device.find_collection(devices, "col05")


if __name__ == "__main__":
    unittest.main()
