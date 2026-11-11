"""Regression tests for the add-on's gas-valve room defaults."""

import json
import unittest
from pathlib import Path


class GasValveRoomDefaultsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config_path = Path(__file__).resolve().parents[1] / "config.json"
        cls.config = json.loads(config_path.read_text(encoding="utf-8"))

    def test_gas_valve_is_configured_in_kitchen(self):
        gas_devices = [
            device for device in self.config["options"]["devices"]
            if device.get("type") == "gas"
        ]
        self.assertEqual(gas_devices, [{"type": "gas", "room": "kitchen"}])

    def test_away_mode_targets_kitchen_gas_valve(self):
        self.assertEqual(self.config["options"]["away_gas_room"], "kitchen")

    def test_away_gas_room_schema_lists_supported_rooms(self):
        self.assertEqual(
            self.config["schema"]["away_gas_room"],
            "list(livingroom|room1|room2|room3|kitchen)",
        )


if __name__ == "__main__":
    unittest.main()
