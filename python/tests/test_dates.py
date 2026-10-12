"""Tests for strict date parsing and overdue arithmetic."""

import unittest
from datetime import date

from reminders.dates import days_overdue, parse_date


class ParseDateTest(unittest.TestCase):
    def test_accepts_a_real_date(self):
        self.assertEqual(parse_date("2026-10-12"), date(2026, 10, 12))

    def test_accepts_a_leap_day(self):
        self.assertEqual(parse_date("2024-02-29"), date(2024, 2, 29))

    def test_rejects_a_day_out_of_range(self):
        self.assertIsNone(parse_date("2026-02-30"))

    def test_rejects_a_non_leap_february_29(self):
        self.assertIsNone(parse_date("2026-02-29"))

    def test_rejects_a_wrong_format(self):
        self.assertIsNone(parse_date("30/09/2026"))

    def test_rejects_a_short_month(self):
        self.assertIsNone(parse_date("2026-2-3"))

    def test_rejects_an_empty_string(self):
        self.assertIsNone(parse_date(""))

    def test_rejects_non_strings(self):
        for value in (None, 20261012, True, ["2026-10-12"]):
            self.assertIsNone(parse_date(value))


class DaysOverdueTest(unittest.TestCase):
    def test_due_today_is_zero(self):
        self.assertEqual(days_overdue(date(2026, 10, 12), date(2026, 10, 12)), 0)

    def test_future_due_date_is_negative(self):
        self.assertEqual(days_overdue(date(2026, 10, 12), date(2026, 10, 20)), -8)

    def test_counts_calendar_days(self):
        self.assertEqual(days_overdue(date(2026, 10, 12), date(2026, 9, 30)), 12)


if __name__ == "__main__":
    unittest.main()
