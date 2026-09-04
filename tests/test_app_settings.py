import json
from pathlib import Path
import tempfile
import unittest

from app_settings import AppSettings, load_settings, save_settings


class AppSettingsTests(unittest.TestCase):
    def test_defaults_are_safe_for_unknown_hardware(self):
        settings = AppSettings()
        self.assertEqual("borderless", settings.display_mode)
        self.assertIsNone(settings.resolution)
        self.assertEqual(1.0, settings.gui_scale)
        self.assertEqual(0.8, settings.game_volume)
        self.assertFalse(settings.muted)

    def test_invalid_and_corrupt_settings_fall_back_safely(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text("not json", encoding="utf-8")
            self.assertEqual(AppSettings(), load_settings(path))
            path.write_text(json.dumps({
                "display_mode": "broken", "display_index": -4,
                "resolution": [10, "large"], "gui_scale": 9,
                "game_volume": 20, "muted": "yes",
            }), encoding="utf-8")
            loaded = load_settings(path)
            self.assertEqual("borderless", loaded.display_mode)
            self.assertEqual(0, loaded.display_index)
            self.assertIsNone(loaded.resolution)
            self.assertEqual(1.2, loaded.gui_scale)
            self.assertEqual(1.0, loaded.game_volume)
            self.assertFalse(loaded.muted)

    def test_save_round_trips_and_leaves_no_temporary_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "settings.json"
            expected = AppSettings("windowed", 1, (1600, 900), 0.9, 0.35, True)
            save_settings(expected, path)
            self.assertEqual(expected, load_settings(path))
            self.assertFalse(path.with_suffix(".json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
