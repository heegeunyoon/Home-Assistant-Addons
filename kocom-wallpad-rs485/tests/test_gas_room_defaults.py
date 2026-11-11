"""Regression tests for gas-valve logical room and RS-485 address separation."""

import json
import unittest
from pathlib import Path

from controller import KocomController


class FakeConfig:
    def get_devices(self):
        return [{"type": "gas", "room": "kitchen"}]

    def get(self, section, key, fallback=None):
        if (section, key) == ("Away", "gas_room"):
            return "livingroom"
        return fallback


async def noop_state(topic, payload):
    pass


class GasValveRoomDefaultsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config_path = Path(__file__).resolve().parents[1] / "config.json"
        cls.config = json.loads(config_path.read_text(encoding="utf-8"))

    def setUp(self):
        self.controller = KocomController(noop_state, FakeConfig())

    def test_gas_valve_is_configured_in_kitchen(self):
        gas_devices = [
            device for device in self.config["options"]["devices"]
            if device.get("type") == "gas"
        ]
        self.assertEqual(gas_devices, [{"type": "gas", "room": "kitchen"}])

    def test_protocol_address_remains_observed_livingroom_code(self):
        # Captured gas frames use room byte 0x00; do not retarget cutoff to kitchen 0x04.
        self.assertEqual(self.config["options"]["away_gas_room"], "livingroom")
        self.assertEqual(self.controller._gas_protocol_room("kitchen"), 0x00)
        self.assertEqual(self.controller._build_gas("kitchen")[6], 0x00)

    def test_state_topic_uses_physical_kitchen_room(self):
        self.assertEqual(self.controller._gas_state_room("livingroom"), "kitchen")

    def test_away_gas_room_schema_lists_supported_rooms(self):
        self.assertEqual(
            self.config["schema"]["away_gas_room"],
            "list(livingroom|room1|room2|room3|kitchen)",
        )


if __name__ == "__main__":
    unittest.main()
