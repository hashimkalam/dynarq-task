"""Tests for the owner's page rendering."""

import unittest

from reminders.page import render_error, render_page

INVOICE = {
    "id": "INV-1",
    "customer": "Example Ltd",
    "amount": 100.0,
    "currency": "EUR",
    "due_date": "2026-10-01",
    "paid_date": None,
}


def action(**overrides):
    base = {
        "invoice_id": "INV-1",
        "step": "firm",
        "needs_approval": True,
        "days_overdue": 11,
        "message": "Pay please.",
    }
    base.update(overrides)
    return base


class RenderPageTest(unittest.TestCase):
    def test_empty_plan_says_nothing_to_do(self):
        html = render_page({"today": "2026-10-12", "actions": [], "skipped": []}, [], {})
        self.assertIn("Nothing to do today.", html)
        self.assertIn("No invoices were skipped.", html)

    def test_approval_actions_show_buttons(self):
        html = render_page(
            {"today": "2026-10-12", "actions": [action()], "skipped": []}, [INVOICE], {}
        )
        self.assertIn('value="approved"', html)
        self.assertIn('value="rejected"', html)
        self.assertIn("EUR 100.00", html)

    def test_friendly_actions_have_no_buttons(self):
        html = render_page(
            {"today": "2026-10-12", "actions": [action(needs_approval=False)], "skipped": []},
            [INVOICE],
            {},
        )
        self.assertNotIn('value="approved"', html)
        self.assertIn("No approval needed for this reminder.", html)

    def test_recorded_decision_is_shown(self):
        html = render_page(
            {"today": "2026-10-12", "actions": [action()], "skipped": []},
            [INVOICE],
            {"INV-1": "rejected"},
        )
        self.assertIn("You rejected this reminder.", html)

    def test_skipped_reasons_are_plain_words_not_codes(self):
        plan = {
            "today": "2026-10-12",
            "actions": [],
            "skipped": [{"invoice_id": "INV-2", "reason": "invalid_due_date"}],
        }
        html = render_page(plan, [], {})
        self.assertIn("The due date is not a real date in YYYY-MM-DD form.", html)
        self.assertNotIn("invalid_due_date", html)

    def test_user_data_is_escaped(self):
        invoice = dict(INVOICE, customer="<script>alert(1)</script>")
        html = render_page(
            {"today": "2026-10-12", "actions": [action()], "skipped": []}, [invoice], {}
        )
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)


class RenderErrorTest(unittest.TestCase):
    def test_error_page_is_friendly(self):
        html = render_error("Could not read the data files.")
        self.assertIn("We could not build today's plan.", html)
        self.assertIn("Could not read the data files.", html)


if __name__ == "__main__":
    unittest.main()
