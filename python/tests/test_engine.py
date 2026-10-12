"""Tests for the rules engine: skips, paid, thresholds, sent and sorting."""

import json
import unittest
from pathlib import Path

from reminders import PlanError, build_plan

TODAY = "2026-10-12"


def invoice(**overrides):
    base = {
        "id": "INV-1001",
        "customer": "Example Ltd",
        "email": "accounts@example.test",
        "amount": 1000.0,
        "currency": "EUR",
        "due_date": "2026-10-01",
        "paid_date": None,
    }
    base.update(overrides)
    return base


def plan(invoices, sent=(), today=TODAY):
    return build_plan(invoices, list(sent), today)


def only_action(result):
    return result["actions"][0]


class ShapeTest(unittest.TestCase):
    def test_empty_input_gives_an_empty_plan(self):
        self.assertEqual(plan([]), {"today": TODAY, "actions": [], "skipped": []})

    def test_bad_today_raises(self):
        with self.assertRaises(PlanError):
            plan([], today="2026-02-30")

    def test_bad_today_is_not_a_real_date_string(self):
        with self.assertRaises(PlanError):
            plan([], today="12/10/2026")


class SkipReasonTest(unittest.TestCase):
    def test_duplicate_id_skipped_once_for_every_copy(self):
        result = plan([invoice(due_date="2026-09-25"), invoice(due_date="2026-09-28")])
        self.assertEqual(
            result["skipped"], [{"invoice_id": "INV-1001", "reason": "duplicate_id"}]
        )
        self.assertEqual(result["actions"], [])

    def test_duplicate_beats_an_otherwise_invalid_sibling(self):
        result = plan([invoice(amount="oops"), invoice()])
        self.assertEqual(result["skipped"][0]["reason"], "duplicate_id")

    def test_invalid_amount_for_a_string(self):
        result = plan([invoice(amount="100")])
        self.assertEqual(result["skipped"], [{"invoice_id": "INV-1001", "reason": "invalid_amount"}])

    def test_invalid_amount_for_a_boolean(self):
        result = plan([invoice(amount=True)])
        self.assertEqual(result["skipped"][0]["reason"], "invalid_amount")

    def test_invalid_amount_for_missing_key(self):
        record = invoice()
        del record["amount"]
        self.assertEqual(plan([record])["skipped"][0]["reason"], "invalid_amount")

    def test_invalid_amount_for_zero_and_negative(self):
        for amount in (0, -5):
            self.assertEqual(plan([invoice(amount=amount)])["skipped"][0]["reason"], "invalid_amount")

    def test_missing_due_date_for_none_missing_and_empty(self):
        none_case = plan([invoice(due_date=None)])
        empty_case = plan([invoice(due_date="")])
        missing = invoice()
        del missing["due_date"]
        missing_case = plan([missing])
        for result in (none_case, empty_case, missing_case):
            self.assertEqual(result["skipped"][0]["reason"], "missing_due_date")

    def test_invalid_due_date_for_unreal_and_malformed(self):
        for due in ("2026-02-30", "30/09/2026"):
            self.assertEqual(plan([invoice(due_date=due)])["skipped"][0]["reason"], "invalid_due_date")

    def test_invalid_paid_date_for_bad_string_and_future(self):
        for paid in ("", "05/10/2026", "2026-11-01"):
            self.assertEqual(plan([invoice(paid_date=paid)])["skipped"][0]["reason"], "invalid_paid_date")

    def test_missing_paid_date_is_valid(self):
        record = invoice(due_date="2026-10-01")
        del record["paid_date"]
        self.assertEqual(plan([record])["skipped"], [])


class PaidAndNotYetTest(unittest.TestCase):
    def test_paid_on_or_before_today_plans_nothing(self):
        for paid in ("2026-10-05", "2026-10-12"):
            result = plan([invoice(due_date="2026-09-01", paid_date=paid)])
            self.assertEqual(result["actions"], [])

    def test_paid_is_true_even_with_sent_reminders(self):
        result = plan(
            [invoice(due_date="2026-09-01", paid_date="2026-10-05")],
            sent=[{"invoice_id": "INV-1001", "step": "friendly", "sent_on": "2026-09-05"}],
        )
        self.assertEqual(result["actions"], [])

    def test_fewer_than_three_days_overdue_plans_nothing(self):
        for due in ("2026-10-10", "2026-10-11", "2026-10-12", "2026-10-20"):
            self.assertEqual(plan([invoice(due_date=due)])["actions"], [])


class StepThresholdTest(unittest.TestCase):
    def test_three_days_is_friendly_without_approval(self):
        action = only_action(plan([invoice(due_date="2026-10-09")]))
        self.assertEqual(action["step"], "friendly")
        self.assertFalse(action["needs_approval"])
        self.assertEqual(action["days_overdue"], 3)

    def test_nine_days_is_friendly(self):
        self.assertEqual(only_action(plan([invoice(due_date="2026-10-03")]))["step"], "friendly")

    def test_ten_days_is_firm_with_approval(self):
        action = only_action(plan([invoice(due_date="2026-10-02")]))
        self.assertEqual(action["step"], "firm")
        self.assertTrue(action["needs_approval"])

    def test_twenty_three_days_is_firm(self):
        self.assertEqual(only_action(plan([invoice(due_date="2026-09-19")]))["step"], "firm")

    def test_twenty_four_days_is_final_with_approval(self):
        action = only_action(plan([invoice(due_date="2026-09-18")]))
        self.assertEqual(action["step"], "final")
        self.assertTrue(action["needs_approval"])

    def test_plans_only_the_highest_step(self):
        result = plan([invoice(due_date="2026-09-30")])
        self.assertEqual(len(result["actions"]), 1)
        self.assertEqual(only_action(result)["step"], "firm")


class SentTest(unittest.TestCase):
    def test_same_step_already_sent_plans_nothing(self):
        result = plan([invoice(due_date="2026-10-02")], sent=[{"invoice_id": "INV-1001", "step": "firm"}])
        self.assertEqual(result["actions"], [])

    def test_a_higher_step_already_sent_plans_nothing(self):
        result = plan([invoice(due_date="2026-10-02")], sent=[{"invoice_id": "INV-1001", "step": "final"}])
        self.assertEqual(result["actions"], [])

    def test_a_lower_step_already_sent_still_plans_the_current_step(self):
        result = plan([invoice(due_date="2026-10-02")], sent=[{"invoice_id": "INV-1001", "step": "friendly"}])
        self.assertEqual(only_action(result)["step"], "firm")

    def test_unknown_invoice_ids_and_steps_are_ignored(self):
        result = plan(
            [invoice(due_date="2026-10-02")],
            sent=[
                {"invoice_id": "INV-9999", "step": "final"},
                {"invoice_id": "INV-1001", "step": "nonsense"},
            ],
        )
        self.assertEqual(only_action(result)["step"], "firm")

    def test_sent_on_is_not_used(self):
        with_date = plan([invoice(due_date="2026-10-02")], sent=[{"invoice_id": "INV-1001", "step": "friendly", "sent_on": "2026-09-01"}])
        without_date = plan([invoice(due_date="2026-10-02")], sent=[{"invoice_id": "INV-1001", "step": "friendly"}])
        self.assertEqual(with_date, without_date)


class SortingTest(unittest.TestCase):
    def test_ids_sort_in_plain_text_order(self):
        result = plan(
            [
                invoice(id="INV-99", due_date="2026-10-02"),
                invoice(id="INV-100", due_date="2026-10-02"),
            ]
        )
        self.assertEqual([a["invoice_id"] for a in result["actions"]], ["INV-100", "INV-99"])

    def test_skipped_is_sorted_by_id(self):
        result = plan(
            [invoice(id="INV-9", amount="x"), invoice(id="INV-10", amount="x")],
        )
        self.assertEqual([s["invoice_id"] for s in result["skipped"]], ["INV-10", "INV-9"])


class SampleDataTest(unittest.TestCase):
    def test_matches_the_sample_answer(self):
        data_dir = Path(__file__).resolve().parent.parent.parent / "data"
        invoices = json.loads((data_dir / "invoices.json").read_text(encoding="utf-8"))
        sent = json.loads((data_dir / "sent.json").read_text(encoding="utf-8"))

        result = build_plan(invoices, sent, TODAY)

        self.assertEqual(
            [(a["invoice_id"], a["step"]) for a in result["actions"]],
            [("INV-1001", "firm"), ("INV-1002", "friendly"), ("INV-1004", "final"),
             ("INV-1009", "firm"), ("INV-1011", "firm")],
        )
        self.assertEqual(
            sorted((s["invoice_id"], s["reason"]) for s in result["skipped"]),
            [("INV-1007", "invalid_due_date"), ("INV-1008", "missing_due_date"),
             ("INV-1010", "duplicate_id")],
        )
        self.assertEqual(only_action(result)["days_overdue"], 12)
        self.assertTrue(result["actions"][0]["needs_approval"])


if __name__ == "__main__":
    unittest.main()
