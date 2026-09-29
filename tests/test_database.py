import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database
from offer import Offer


def make_offer(**changes):
    values = dict(
        source="Testquelle",
        title="Stellplatz",
        address="Franz-Klühs-Straße 1, Berlin",
        price="50 €",
        link="",
        latitude=52.5,
        longitude=13.4,
    )
    values.update(changes)
    return Offer(**values)


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_file = Path(self.temp_dir.name) / "data" / "known_offers.json"
        self.database_patch = patch.object(database, "DATABASE_FILE", self.database_file)
        self.database_patch.start()
        self.addCleanup(self.database_patch.stop)
        self.addCleanup(self.temp_dir.cleanup)

    def test_empty_links_use_offer_details_for_identity(self):
        first = make_offer(address="Street 1")
        same = make_offer(address=" Street   1 ")
        other = make_offer(address="Street 2")

        self.assertEqual(database.offer_key(first), database.offer_key(same))
        self.assertNotEqual(database.offer_key(first), database.offer_key(other))
        self.assertEqual(database.get_new_offers([same, other], [first]), [other])

    def test_offers_without_any_identity_are_not_collapsed(self):
        blank = make_offer(source="", title="", address="", price="")
        no_details = make_offer(title="", address="", price="")
        self.assertIsNone(database.offer_key(blank))
        self.assertIsNone(database.offer_key(no_details))
        self.assertEqual(database.get_new_offers([blank], [blank]), [blank])

    def test_link_identity_is_stable_and_ignores_fragment_and_trailing_slash(self):
        first = make_offer(link="HTTPS://Example.COM/listing/123/#photo")
        same = make_offer(link="https://example.com/listing/123")
        self.assertEqual(database.offer_key(first), database.offer_key(same))
        self.assertNotEqual(
            database.offer_key(make_offer(link="https://example.com/Listing/123")),
            database.offer_key(make_offer(link="https://example.com/listing/123")),
        )

    def test_corrupt_and_empty_database_are_preserved_and_reported(self):
        self.database_file.parent.mkdir()
        for content in ("{bad json", "", "{}", "[]"):
            self.database_file.write_text(content, encoding="utf-8")
            with self.subTest(content=content), self.assertRaises(database.DatabaseError):
                database.load_known_offers()
            self.assertEqual(self.database_file.read_text(encoding="utf-8"), content)

    def test_save_is_valid_json_and_round_trips(self):
        expected = [make_offer()]
        database.save_known_offers(expected)
        self.assertEqual(database.load_known_offers(), [expected[0].__dict__])
        self.assertEqual(json.loads(self.database_file.read_text(encoding="utf-8")), [expected[0].__dict__])

    def test_failed_atomic_replace_preserves_existing_database(self):
        original = json.dumps([make_offer().__dict__])
        self.database_file.parent.mkdir()
        self.database_file.write_text(original, encoding="utf-8")
        with patch.object(database.os, "replace", side_effect=OSError("disk unavailable")):
            with self.assertRaises(database.DatabaseError):
                database.save_known_offers([make_offer(title="replacement")])
        self.assertEqual(self.database_file.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
