"""
Tests for invoice storage and auto-send rules.
"""

import unittest
from datetime import datetime
from unittest.mock import patch

from service import datetime_for_month
from service import parse_month_key
from service import should_auto_send
from storage import month_key
from storage import trim_sent_history


class TrimSentHistoryTests(unittest.TestCase):
    """
    Tests for 12-month retention of sent history.
    """

    def test_keeps_only_last_twelve_months(self):
        """
        Older month keys are dropped when history exceeds 12 entries.
        """
        sent = {
            f"2025-{month:02d}": {"invoice_number": f"UWHPL-{month:04d}"}
            for month in range(1, 13)
        }
        sent["2026-01"] = {"invoice_number": "UWHPL-0013"}
        trimmed = trim_sent_history(sent)
        self.assertEqual(len(trimmed), 12)
        self.assertNotIn("2025-01", trimmed)
        self.assertIn("2026-01", trimmed)
        self.assertIn("2025-02", trimmed)


class ShouldAutoSendTests(unittest.TestCase):
    """
    Tests for monthly catch-up auto-send gating.
    """

    def test_before_send_day_returns_false(self):
        """
        Auto-send waits until the configured day of month.
        """
        config = {"send_day": 25}
        now = datetime(2026, 7, 24, 10, 0, 0)
        with patch("service.was_sent_for_month", return_value=False):
            self.assertFalse(should_auto_send(config, now))

    def test_on_or_after_send_day_when_not_sent(self):
        """
        Auto-send runs on/after send day if month is unpaid.
        """
        config = {"send_day": 25}
        now = datetime(2026, 7, 26, 10, 0, 0)
        with patch("service.was_sent_for_month", return_value=False):
            self.assertTrue(should_auto_send(config, now))

    def test_skips_when_already_sent(self):
        """
        Auto-send does not repeat a month already recorded.
        """
        config = {"send_day": 25}
        now = datetime(2026, 7, 26, 10, 0, 0)
        with patch("service.was_sent_for_month", return_value=True):
            self.assertFalse(should_auto_send(config, now))

    def test_auto_send_checks_current_month_only(self):
        """
        Auto-send asks only about the current month key.
        """
        config = {"send_day": 25}
        now = datetime(2026, 7, 28, 10, 0, 0)
        with patch("service.was_sent_for_month", return_value=False) as sent_check:
            self.assertTrue(should_auto_send(config, now))
            sent_check.assert_called_once_with(month_key(now))


class MonthParsingTests(unittest.TestCase):
    """
    Tests for manual past-month invoice targeting.
    """

    def test_parse_month_key(self):
        """
        Valid YYYY-MM values parse into year and month.
        """
        self.assertEqual(parse_month_key("2026-06"), (2026, 6))

    def test_parse_month_key_rejects_invalid(self):
        """
        Invalid month strings raise ValueError.
        """
        with self.assertRaises(ValueError):
            parse_month_key("2026/06")

    def test_datetime_for_month_uses_send_day(self):
        """
        Invoice date uses the configured send day within the month.
        """
        dt = datetime_for_month("2026-06", send_day=25)
        self.assertEqual(dt, datetime(2026, 6, 25))


if __name__ == "__main__":
    unittest.main()
