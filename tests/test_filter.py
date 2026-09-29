import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import filter as offer_filter


class FilterTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_file = Path(self.temp_dir.name) / "coordinates.json"
        self.cache_patch = patch.object(offer_filter, "CACHE_FILE", self.cache_file)
        self.cache_patch.start()
        self.addCleanup(self.cache_patch.stop)
        self.addCleanup(self.temp_dir.cleanup)
        offer_filter.coordinate_cache.clear()

    def test_cache_loader_keeps_only_valid_coordinate_pairs(self):
        self.cache_file.write_text(
            json.dumps(
                {
                    "valid": [52.5, 13.4],
                    "wrong length": [52.5],
                    "out of range": [91, 13.4],
                    "not numbers": ["north", 13.4],
                    "nan": [float("nan"), 13.4],
                }
            ),
            encoding="utf-8",
        )
        self.assertEqual(offer_filter.load_cache(), {"valid": [52.5, 13.4]})

    def test_malformed_or_non_object_cache_returns_empty(self):
        for content in ("{bad", "[]", ""):
            with self.subTest(content=content):
                self.cache_file.write_text(content, encoding="utf-8")
                self.assertEqual(offer_filter.load_cache(), {})

    def test_radius_uses_supplied_coordinates_without_network(self):
        inside, distance = offer_filter.is_within_radius(
            (52.5010916, 13.3941283), "ignored", 2.0, (52.501, 13.394)
        )
        self.assertTrue(inside)
        self.assertLess(distance, 2.0)

    def test_cache_write_failure_is_non_fatal(self):
        with patch.object(offer_filter.os, "replace", side_effect=OSError("disk unavailable")):
            offer_filter.save_cache({"address": [52.5, 13.4]})
        self.assertFalse(self.cache_file.exists())

    def test_invalid_offer_coordinates_fall_back_to_geocoded_address(self):
        with patch.object(offer_filter, "get_coordinates", return_value=(52.501, 13.394)) as geocode:
            inside, distance = offer_filter.is_within_radius(
                (52.5010916, 13.3941283), "address", 2.0, (float("nan"), 0)
            )
        geocode.assert_called_once_with("address")
        self.assertTrue(inside)
        self.assertIsNotNone(distance)


if __name__ == "__main__":
    unittest.main()
