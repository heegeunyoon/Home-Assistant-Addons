"""Unit tests for the Kocom outlet physical/logical address translation."""

import asyncio
import unittest
from types import SimpleNamespace

from const import CMD_STATE, OUTLET_ADDRESS_MAP, OUTLET_ROOM_MAP
from controller import KocomController


class FakeConfig:
    def __init__(self, devices=None):
        self.devices = devices or []

    def get_devices(self):
        return list(self.devices)

    def get_switch_count(self, dev_type, room):
        return sum(
            1 for item in self.devices
            if item.get("type") == dev_type
            and item.get("room", "livingroom") == room
        ) or 1


class OutletMappingTests(unittest.TestCase):
    def test_all_physical_addresses_have_expected_logical_mapping(self):
        self.assertEqual(
            OUTLET_ROOM_MAP,
            {
                0x00: ("livingroom", 1),
                0x01: ("livingroom", 2),
                0x02: ("room1", 1),
                0x03: ("room1", 2),
                0x04: ("room2", 1),
                0x05: ("room3", 1),
                0x06: ("kitchen", 1),
                0x07: ("kitchen", 2),
            },
        )
        for address, logical in OUTLET_ROOM_MAP.items():
            self.assertEqual(OUTLET_ADDRESS_MAP[logical], address)

    def test_queries_cover_each_configured_livingroom_outlet(self):
        config = FakeConfig([
            {"type": "outlet", "room": "livingroom"},
            {"type": "outlet", "room": "livingroom"},
        ])
        controller = KocomController(lambda *_: asyncio.sleep(0), config)
        packets = controller.build_outlet_queries("livingroom")
        self.assertEqual([packet[6] for packet in packets], [0x00, 0x01])
        self.assertEqual(len(controller.build_all_outlet_queries()), 8)

    def test_command_for_logical_outlet_2_uses_physical_address_01(self):
        config = FakeConfig([
            {"type": "outlet", "room": "livingroom"},
            {"type": "outlet", "room": "livingroom"},
        ])
        controller = KocomController(lambda *_: asyncio.sleep(0), config)
        packets = controller.build_command("outlet", "livingroom", "on", index=2)
        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0][6], 0x01)
        self.assertEqual(packets[0][10], 0xFF)

    def test_state_reports_merge_by_logical_room_and_channel(self):
        config = FakeConfig([
            {"type": "outlet", "room": "livingroom"},
            {"type": "outlet", "room": "livingroom"},
        ])
        published = []

        async def on_state(topic, payload):
            published.append((topic, payload))

        controller = KocomController(on_state, config)

        async def run():
            for address, value in ((0x00, 0xFF), (0x01, 0x00)):
                frame = SimpleNamespace(
                    command=CMD_STATE,
                    is_state_report=True,
                    dev_room=address,
                    payload=bytes([value]) + bytes(7),
                )
                await controller._pub_switch(frame, "outlet")

        asyncio.run(run())
        self.assertEqual(published[-1][0], "kocom/livingroom/outlet/state")
        self.assertEqual(
            published[-1][1],
            {"outlet_1": "on", "outlet_2": "off"},
        )

    def test_unconfigured_outlet_count_uses_known_physical_map(self):
        controller = KocomController(lambda *_: asyncio.sleep(0), FakeConfig())
        self.assertEqual(controller._switch_count("outlet", "livingroom"), 2)
        self.assertEqual(controller._switch_count("outlet", "room1"), 2)
        self.assertEqual(controller._switch_count("outlet", "room2"), 1)


if __name__ == "__main__":
    unittest.main()
