"""Tests for amount formatting and the per-step reminder messages."""

import re
import unittest

from reminders.messages import build_message, format_amount

REQUIRED_STEPS = ("friendly", "firm", "final")


def make_message(step, **overrides):
    fields = {
        "customer": "Alder Fabrication Ltd",
        "invoice_id": "INV-1001",
        "due_date": "2026-09-30",
        "amount": 1250.0,
        "currency": "EUR",
        "days_overdue": 12,
    }
    fields.update(overrides)
    return build_message(step=step, **fields)


class FormatAmountTest(unittest.TestCase):
    def test_pads_to_two_decimals(self):
        self.assertEqual(format_amount(215.5, "EUR"), "EUR 215.50")

    def test_keeps_two_decimals(self):
        self.assertEqual(format_amount(845.25, "USD"), "USD 845.25")

    def test_formats_whole_numbers(self):
        self.assertEqual(format_amount(1250, "EUR"), "EUR 1250.00")


class BuildMessageTest(unittest.TestCase):
    def test_every_step_includes_the_required_fields(self):
        for step in REQUIRED_STEPS:
            message = make_message(step)
            self.assertIn("Alder Fabrication Ltd", message)
            self.assertIn("INV-1001", message)
            self.assertIn("2026-09-30", message)
            self.assertIn("EUR 1250.00", message)
            self.assertIn("12 days overdue", message)

    def test_only_the_amount_is_a_decimal_figure(self):
        for step in REQUIRED_STEPS:
            message = make_message(step)
            self.assertEqual(re.findall(r"\d+\.\d+", message), ["1250.00"])

    def test_makes_no_invented_charges_or_claims(self):
        for step in REQUIRED_STEPS:
            lowered = make_message(step).lower()
            for banned in ("fee", "interest", "penalty", "%", "reminded"):
                self.assertNotIn(banned, lowered)

    def test_steps_read_differently(self):
        friendly, firm, final = (make_message(step) for step in REQUIRED_STEPS)
        self.assertEqual(len({friendly, firm, final}), 3)


if __name__ == "__main__":
    unittest.main()
