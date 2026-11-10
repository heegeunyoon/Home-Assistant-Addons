"""Regression tests for captured Kocom elevator event packets."""

import asyncio
import unittest

from controller import KocomController
from models import PacketFrame


class FakeConfig:
    def get(self, section, option, fallback=None):
        return fallback


class ElevatorEventTests(unittest.TestCase):
    def setUp(self):
        self.published = []

        async def on_state(topic, payload):
            self.published.append((topic, payload))

        self.controller = KocomController(on_state, FakeConfig())

    def run_packet(self, packet_hex):
        frame = PacketFrame(bytes.fromhex(packet_hex))
        self.assertTrue(frame.is_valid, packet_hex)
        asyncio.run(self.controller._pub_elevator(frame))

    def test_captured_call_event_is_published(self):
        # elevator(0x44) -> wallpad(0x01), command=0x01, payload[0]=0x00
        self.run_packet("aa5530bc0001004400010000000000000000320d0d")
        self.assertEqual(
            self.published,
            [("kocom/myhome/elevator/state",
              {"state": "on", "direction": "called"})],
        )

    def test_captured_cmd_state_arrival_is_published(self):
        # wallpad(0x01) -> elevator(0x44), command=0x00, payload[0]=0x03
        self.run_packet("aa5530bc0044000100000300000000000000340d0d")
        self.assertEqual(
            self.published,
            [("kocom/myhome/elevator/state",
              {"state": "off", "direction": "arrival"})],
        )

    def test_cmd_on_arrival_variant_remains_supported(self):
        # Captured companion notification: same direction/event, command=0x01
        self.run_packet("aa5530bc0044000100010300000000000000350d0d")
        self.assertEqual(self.published[-1][1],
                         {"state": "off", "direction": "arrival"})

    def test_wrong_direction_is_ignored(self):
        # Arrival payload from elevator -> wallpad is not a valid arrival report.
        self.run_packet("aa5530bc0001004400010300000000000000330d0d")
        self.assertEqual(self.published, [])

    def test_ack_is_ignored(self):
        self.run_packet("aa5530dc0044000100010300000000000000550d0d")
        self.assertEqual(self.published, [])


if __name__ == "__main__":
    unittest.main()
