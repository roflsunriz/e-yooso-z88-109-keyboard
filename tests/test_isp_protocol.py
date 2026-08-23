import unittest

import isp_protocol


class FakeCommandDevice:
    def __init__(self) -> None:
        self.sent: list[bytes] = []

    def send_feature_report(self, data: bytes) -> int:
        self.sent.append(data)
        return len(data)


class FakeTransferDevice:
    def __init__(self, pages: list[bytes]) -> None:
        self.pages = pages
        self.requests: list[tuple[int, int]] = []

    def get_feature_report(self, report_id: int, length: int) -> list[int]:
        self.requests.append((report_id, length))
        return list(bytes((0x06, 0x72)) + self.pages.pop(0))


class ISPProtocolTests(unittest.TestCase):
    def test_rejects_flash_mutating_commands(self) -> None:
        for opcode in (0x55, 0x57, 0x45):
            with self.subTest(opcode=opcode), self.assertRaises(ValueError):
                isp_protocol.command(opcode)

    def test_encodes_only_allowed_commands(self) -> None:
        self.assertEqual(
            isp_protocol.command(isp_protocol.COMMAND_ENTER_ISP),
            bytes((0x05, 0x75, 0, 0, 0, 0)),
        )
        self.assertEqual(
            isp_protocol.command(isp_protocol.COMMAND_INIT_READ, 0x1234),
            bytes((0x05, 0x52, 0x34, 0x12, 0, 0)),
        )
        self.assertEqual(
            isp_protocol.command(isp_protocol.COMMAND_REBOOT),
            bytes((0x05, 0x5A, 0, 0, 0, 0)),
        )

    def test_reads_all_pages_without_write_or_enable_command(self) -> None:
        command_device = FakeCommandDevice()
        transfer_device = FakeTransferDevice([b"ABCD", b"EFGH"])

        result = isp_protocol.read_firmware(
            command_device,
            transfer_device,
            firmware_size=8,
            page_size=4,
        )

        self.assertEqual(result, b"ABCDEFGH")
        self.assertEqual(
            command_device.sent,
            [bytes((0x05, 0x52, 0, 0, 0, 0))],
        )
        self.assertEqual(transfer_device.requests, [(0x06, 6), (0x06, 6)])

    def test_rejects_wrong_transfer_header(self) -> None:
        class WrongTransferDevice(FakeTransferDevice):
            def get_feature_report(self, report_id: int, length: int) -> list[int]:
                return list(bytes((0x06, 0x77)) + b"ABCD")

        with self.assertRaisesRegex(OSError, "応答ヘッダー"):
            isp_protocol.read_firmware(
                FakeCommandDevice(),
                WrongTransferDevice([]),
                firmware_size=4,
                page_size=4,
            )


if __name__ == "__main__":
    unittest.main()
