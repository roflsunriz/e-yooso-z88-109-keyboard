import argparse
import unittest

import rgb_cli


class RGBCLITests(unittest.TestCase):
    def test_parses_hash_prefixed_color(self) -> None:
        self.assertEqual(rgb_cli.parse_color("#12ABEF"), (0x12, 0xAB, 0xEF))

    def test_rejects_invalid_color(self) -> None:
        for value in ("123", "GG0000", "12345678"):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                rgb_cli.parse_color(value)

    def test_rainbow_frame_fills_all_slots(self) -> None:
        frame = rgb_cli.rainbow_frame(0.0)

        self.assertEqual(len(frame), 126)
        self.assertTrue(all(0 <= component <= 255 for color in frame for component in color))


if __name__ == "__main__":
    unittest.main()
