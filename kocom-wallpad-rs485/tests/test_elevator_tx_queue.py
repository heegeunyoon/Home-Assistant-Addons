"""Tests for elevator call state publication after queued RS-485 transmission."""

import asyncio
import contextlib
import unittest

from kocom import KocomBridge


class FakeRS485:
    def __init__(self, send_result=True, connected=True):
        self.send_result = send_result
        self.connected = connected
        self.sent = []

    def is_connected(self):
        return self.connected

    def idle_since(self):
        return 10.0

    async def send(self, packet):
        self.sent.append(packet)
        return self.send_result


class FakeController:
    def __init__(self):
        self.diag = {"tx_total": 0}
        self.called = 0

    async def publish_elevator_called(self):
        self.called += 1


class ElevatorTxQueueTests(unittest.IsolatedAsyncioTestCase):
    async def run_sender_once(self, send_result=True, connected=True):
        bridge = KocomBridge.__new__(KocomBridge)
        bridge._tx_queue = asyncio.Queue()
        bridge._rs485 = FakeRS485(send_result=send_result, connected=connected)
        bridge._ctrl = FakeController()

        task = asyncio.create_task(bridge._sender_loop())
        await bridge._tx_queue.put((b"elevator-call-packet", True))
        await asyncio.wait_for(bridge._tx_queue.join(), timeout=2)
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        return bridge

    async def test_successful_rs485_write_publishes_call_state(self):
        bridge = await self.run_sender_once(send_result=True)
        self.assertEqual(bridge._ctrl.called, 1)
        self.assertEqual(bridge._ctrl.diag["tx_total"], 1)

    async def test_failed_rs485_write_does_not_publish_call_state(self):
        bridge = await self.run_sender_once(send_result=False)
        self.assertEqual(bridge._ctrl.called, 0)
        self.assertEqual(bridge._ctrl.diag["tx_total"], 0)

    async def test_disconnected_rs485_does_not_publish_call_state(self):
        bridge = await self.run_sender_once(connected=False)
        self.assertEqual(bridge._ctrl.called, 0)
        self.assertEqual(bridge._ctrl.diag["tx_total"], 0)


if __name__ == "__main__":
    unittest.main()
