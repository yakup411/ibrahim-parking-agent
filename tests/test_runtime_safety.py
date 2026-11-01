import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import agent
import database
import source_manager
import telegram_bot
from offer import Offer


def make_offer(title, link):
    return Offer(
        source="Testquelle",
        title=title,
        address="Franz-Klühs-Straße 4, Berlin",
        price="50 €",
        link=link,
        latitude=52.501,
        longitude=13.394,
    )


class RuntimeSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_file = Path(self.temp_dir.name) / "known_offers.json"
        self.db_patch = patch.object(database, "DATABASE_FILE", self.database_file)
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        self.addCleanup(self.temp_dir.cleanup)

    def test_source_failure_does_not_prevent_other_source(self):
        good_offer = make_offer("good", "https://example.com/good")
        with patch.object(source_manager, "get_stadtundland_offers", side_effect=OSError("down")), patch.object(
            source_manager, "get_gewobag_offers", return_value=[good_offer]
        ) as good_source:
            self.assertEqual(source_manager.get_all_offers(), [good_offer])
        good_source.assert_called_once_with()

    def test_all_source_failures_are_reported(self):
        with patch.object(source_manager, "get_stadtundland_offers", side_effect=OSError("one")), patch.object(
            source_manager, "get_gewobag_offers", side_effect=OSError("two")
        ), self.assertRaises(RuntimeError):
            source_manager.get_all_offers()

    def test_empty_existing_database_does_not_trigger_a_false_first_start(self):
        self.database_file.write_text("[]", encoding="utf-8")
        with patch.object(agent, "get_all_offers") as fetch:
            agent.main()
        fetch.assert_not_called()
        self.assertEqual(self.database_file.read_text(encoding="utf-8"), "[]")

    def test_missing_database_keeps_the_intended_first_start_behavior(self):
        initial_offer = make_offer("initial", "https://example.com/initial")
        with patch.object(agent, "get_all_offers", return_value=[initial_offer]), patch.object(
            agent, "send_telegram_message"
        ) as send:
            agent.main()
        send.assert_not_called()
        self.assertEqual(database.load_known_offers(), [initial_offer.__dict__])

    def test_failed_telegram_offer_is_not_saved_but_success_is_not_resent(self):
        known = make_offer("old", "https://example.com/old")
        failed = make_offer("failed", "https://example.com/failed")
        succeeded = make_offer("succeeded", "https://example.com/succeeded")
        database.save_known_offers([known])
        send_calls = []

        def send(message):
            send_calls.append(message)
            if "failed" in message:
                raise ConnectionError("Telegram unavailable")

        with patch.object(agent, "get_all_offers", return_value=[known, failed, succeeded, succeeded]), patch.object(
            agent, "is_within_radius", return_value=(True, 0.1)
        ), patch.object(agent, "send_telegram_message", side_effect=send):
            agent.main()
            agent.main()

        saved = database.load_known_offers()
        links = {item["link"] for item in saved}
        self.assertIn(succeeded.link, links)
        self.assertNotIn(failed.link, links)
        self.assertEqual(sum("failed" in message for message in send_calls), 2)
        self.assertEqual(sum("succeeded" in message for message in send_calls), 1)

    def test_bad_single_offer_does_not_stop_later_offers(self):
        known = make_offer("old", "https://example.com/old")
        bad = make_offer("bad", "https://example.com/bad")
        bad.address = "Malformed address"
        good = make_offer("good", "https://example.com/good")
        database.save_known_offers([known])

        def radius(**kwargs):
            if kwargs["offer_address"] == bad.address:
                raise ValueError("bad offer")
            return True, 0.1

        with patch.object(agent, "get_all_offers", return_value=[known, bad, good]), patch.object(
            agent, "is_within_radius", side_effect=radius
        ), patch.object(agent, "send_telegram_message") as send:
            agent.main()

        self.assertEqual(send.call_count, 1)
        self.assertIn(good.link, {item["link"] for item in database.load_known_offers()})
        self.assertNotIn(bad.link, {item["link"] for item in database.load_known_offers()})

    def test_telegram_http_failure_is_propagated_to_caller(self):
        with patch.object(telegram_bot, "BOT_TOKEN", "test-token"), patch.object(
            telegram_bot, "CHAT_ID", "test-chat"
        ), patch.object(telegram_bot.requests, "post", side_effect=ConnectionError("offline")):
            with self.assertRaises(ConnectionError):
                telegram_bot.send_telegram_message("test only")

    def test_telegram_retries_only_a_connect_timeout(self):
        response = Mock(status_code=200)
        response.json.return_value = {"ok": True}
        with patch.object(telegram_bot, "BOT_TOKEN", "test-token"), patch.object(
            telegram_bot, "CHAT_ID", "test-chat"
        ), patch.object(
            telegram_bot.requests,
            "post",
            side_effect=[telegram_bot.requests.ConnectTimeout(), response],
        ) as post, patch.object(telegram_bot.time, "sleep") as sleep:
            self.assertEqual(telegram_bot.send_telegram_message("test only"), {"ok": True})
        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(0.5)

    def test_telegram_respects_rate_limit_with_a_capped_retry(self):
        limited = Mock(status_code=429)
        limited.json.return_value = {"parameters": {"retry_after": 100}}
        success = Mock(status_code=200)
        success.json.return_value = {"ok": True}
        with patch.object(telegram_bot, "BOT_TOKEN", "test-token"), patch.object(
            telegram_bot, "CHAT_ID", "test-chat"
        ), patch.object(telegram_bot.requests, "post", side_effect=[limited, success]), patch.object(
            telegram_bot.time, "sleep"
        ) as sleep:
            telegram_bot.send_telegram_message("test only")
        sleep.assert_called_once_with(5.0)

    def test_workflow_keeps_cron_and_prevents_overlapping_runs(self):
        workflow = Path(".github/workflows/parking-agent.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "*/15 * * * *"', workflow)
        self.assertIn("concurrency:", workflow)
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertIn("python -m unittest discover -s tests -v", workflow)
        self.assertIn("if: github.event_name != 'pull_request'", workflow)
        self.assertEqual(workflow.count("runs-on: ubuntu-24.04"), 3)
        self.assertIn("gh workflow run parking-agent.yml --ref main", workflow)

    def test_source_http_retry_policy_is_bounded(self):
        from http_client import source_session

        adapter = source_session.get_adapter("https://example.com")
        self.assertEqual(adapter.max_retries.total, 2)
        self.assertEqual(adapter.max_retries.backoff_factor, 0.5)


if __name__ == "__main__":
    unittest.main()
