"""Regression tests for captured Kocom elevator event packets and idle timeout."""

import asyncio
import unittest
from unittest.mock import patch

from controller import KocomController
from models import PacketFrame


class FakeConfig:
    def get(self, section, option, fallback=None):
        return fallback


class ElevatorEventTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.published = []

        async def on_state(topic, payload):
            self.published.append((topic, payload))

        self.controller = KocomController(on_state, FakeConfig())

    async def asyncTearDown(self):
        for task in (
            self.controller._elevator_idle_task,
            self.controller._elevator_call_task,
        ):
            if task and not task.done():
                task.cancel()
        await asyncio.sleep(0)

    async def run_packet(self, packet_hex):
        frame = PacketFrame(bytes.fromhex(packet_hex))
        self.assertTrue(frame.is_valid, packet_hex)
        await self.controller._pub_elevator(frame)

    async def test_captured_call_event_is_published(self):
        await self.run_packet("aa5530bc0001004400010000000000000000320d0d")
        self.assertEqual(
            self.published,
            [("kocom/myhome/elevator/state",
              {"state": "on", "direction": "called"})],
        )

    async def test_captured_cmd_state_arrival_is_published(self):
        await self.run_packet("aa5530bc0044000100000300000000000000340d0d")
        self.assertEqual(
            self.published,
            [("kocom/myhome/elevator/state",
              {"state": "off", "direction": "arrival"})],
        )

    async def test_cmd_on_arrival_variant_remains_supported(self):
        await self.run_packet("aa5530bc0044000100010300000000000000350d0d")
        self.assertEqual(self.published[-1][1],
                         {"state": "off", "direction": "arrival"})

    async def test_wrong_direction_is_ignored(self):
        await self.run_packet("aa5530bc0001004400010300000000000000350d0d")
        self.assertEqual(self.published, [])

    async def test_ack_is_ignored(self):
        await self.run_packet("aa5530dc0044000100010300000000000000550d0d")
        self.assertEqual(self.published, [])

    async def test_successful_tx_call_state_is_published(self):
        await self.controller.publish_elevator_called()
        self.assertEqual(
            self.published,
            [("kocom/myhome/elevator/state",
              {"state": "on", "direction": "called"})],
        )

    async def test_arrival_returns_to_idle_after_ten_seconds(self):
        with patch("controller.ELEVATOR_IDLE_TIMEOUT_SECONDS", 0.01):
            await self.run_packet("aa5530bc0044000100000300000000000000340d0d")
            await asyncio.sleep(0.03)
        self.assertEqual(
            self.published[-1],
            ("kocom/myhome/elevator/state",
             {"state": "off", "direction": "idle"}),
        )

    async def test_called_does_not_return_to_idle_before_arrival(self):
        with patch("controller.ELEVATOR_CALL_TIMEOUT_SECONDS", 0.08):
            with patch("controller.ELEVATOR_IDLE_TIMEOUT_SECONDS", 0.06):
                await self.controller.publish_elevator_called()
                await asyncio.sleep(0.03)
                self.assertEqual(self.published[-1][1]["direction"], "called")
                await self.run_packet("aa5530bc0044000100000300000000000000340d0d")
                await asyncio.sleep(0.03)
                self.assertEqual(self.published[-1][1]["direction"], "arrival")
                await asyncio.sleep(0.04)
        self.assertEqual(self.published[-1][1]["direction"], "idle")

    async def test_called_falls_back_to_idle_after_call_timeout(self):
        with patch("controller.ELEVATOR_CALL_TIMEOUT_SECONDS", 0.01):
            await self.controller.publish_elevator_called()
            await asyncio.sleep(0.03)
        self.assertEqual(self.published[-1][1]["direction"], "idle")

    async def test_arrival_cancels_call_timeout(self):
        with patch("controller.ELEVATOR_CALL_TIMEOUT_SECONDS", 0.04):
            with patch("controller.ELEVATOR_IDLE_TIMEOUT_SECONDS", 0.08):
                await self.controller.publish_elevator_called()
                await asyncio.sleep(0.01)
                await self.run_packet("aa5530bc0044000100000300000000000000340d0d")
                await asyncio.sleep(0.05)
                self.assertEqual(self.published[-1][1]["direction"], "arrival")
                await asyncio.sleep(0.05)
        self.assertEqual(self.published[-1][1]["direction"], "idle")


if __name__ == "__main__":
    unittest.main()
