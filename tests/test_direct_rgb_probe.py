import unittest

import z88_rgb


class FakeDevice:
    def __init__(self) -> None:
        self.sent: list[bytes] = []

    def send_feature_report(self, data: bytes) -> int:
        self.sent.append(data)
        return len(data)


class DirectRGBProbeTests(unittest.TestCase):
    def test_builds_descriptor_sized_uniform_packet(self) -> None:
        packet = z88_rgb.build_packet(z88_rgb.uniform_frame((255, 0, 0)))

        self.assertEqual(len(packet), 382)
        self.assertEqual(packet[:4], bytes((0x08, 0x0A, 0x7A, 0x01)))
        self.assertEqual(packet[4:], bytes((255, 0, 0)) * 126)

    def test_initializes_video_mode_with_three_zero_packets_and_pauses(self) -> None:
        device = FakeDevice()
        pauses: list[float] = []

        controller = z88_rgb.Z88RGBController(None, pauses.append)
        controller._device = device
        controller.initialize_video_mode()

        zero = z88_rgb.build_packet(z88_rgb.uniform_frame((0, 0, 0)))
        self.assertEqual(device.sent, [zero, zero, zero])
        self.assertEqual(pauses, [0.016, 0.016, 0.016])


if __name__ == "__main__":
    unittest.main()
