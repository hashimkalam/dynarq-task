"""The rules engine: turn invoices and sent history into today's plan.

Rules follow README part 1. Each invoice is skipped for the first reason that
applies, a paid or not-yet-due invoice plans nothing, and otherwise the highest
step reached is planned once unless that step or a higher one was already sent.
"""

from collections import Counter

from .dates import days_overdue, parse_date
from .messages import build_message

# name, days overdue at which the step applies, whether the owner must approve.
STEPS = (
    ("friendly", 3, False),
    ("firm", 10, True),
    ("final", 24, True),
)
STEP_RANK = {name: rank for rank, (name, _, _) in enumerate(STEPS)}
VALID_SENT_STEPS = set(STEP_RANK)


class PlanError(ValueError):
    """Raised when the plan cannot be built, for example for an invalid today."""


def parse_today(value):
    """Return today's date or raise PlanError when it is not a real date."""
    parsed = parse_date(value)
    if parsed is None:
        raise PlanError(f"today must be a real date as YYYY-MM-DD, got {value!r}")
    return parsed


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def skip_reason(invoice, duplicate_ids, today):
    """Return the first skip reason for an invoice, or None when it is usable."""
    if invoice.get("id") in duplicate_ids:
        return "duplicate_id"

    amount = invoice.get("amount")
    if not _is_number(amount) or amount <= 0:
        return "invalid_amount"

    due_date = invoice.get("due_date")
    if due_date is None or due_date == "":
        return "missing_due_date"
    if parse_date(due_date) is None:
        return "invalid_due_date"

    paid_date = invoice.get("paid_date")
    if paid_date is not None:
        paid = parse_date(paid_date)
        if paid is None or paid > today:
            return "invalid_paid_date"

    return None


def _highest_step(overdue):
    highest = None
    for name, threshold, needs_approval in STEPS:
        if overdue >= threshold:
            highest = (name, needs_approval)
    return highest


def _sent_steps_by_invoice(sent):
    result = {}
    for entry in sent:
        if isinstance(entry, dict) and entry.get("step") in VALID_SENT_STEPS:
            result.setdefault(entry.get("invoice_id"), set()).add(entry["step"])
    return result


def _plan_action(invoice, sent_steps, today):
    due = parse_date(invoice["due_date"])
    overdue = days_overdue(today, due)

    highest = _highest_step(overdue)
    if highest is None:
        return None

    step, needs_approval = highest
    if any(STEP_RANK[sent] >= STEP_RANK[step] for sent in sent_steps):
        return None

    message = build_message(
        step=step,
        customer=invoice["customer"],
        invoice_id=invoice["id"],
        due_date=invoice["due_date"],
        amount=invoice["amount"],
        currency=invoice["currency"],
        days_overdue=overdue,
    )
    return {
        "invoice_id": invoice["id"],
        "step": step,
        "needs_approval": needs_approval,
        "days_overdue": overdue,
        "message": message,
    }


def build_plan(invoices, sent, today):
    """Return the plan for `today` with today, actions and skipped, both sorted."""
    today_date = parse_today(today)

    id_counts = Counter(invoice.get("id") for invoice in invoices)
    duplicate_ids = {invoice_id for invoice_id, count in id_counts.items() if count > 1}
    sent_steps = _sent_steps_by_invoice(sent)

    actions = []
    skipped = []
    seen_duplicates = set()

    for invoice in invoices:
        reason = skip_reason(invoice, duplicate_ids, today_date)

        if reason == "duplicate_id":
            invoice_id = invoice.get("id")
            if invoice_id not in seen_duplicates:
                seen_duplicates.add(invoice_id)
                skipped.append({"invoice_id": invoice_id, "reason": reason})
            continue

        if reason is not None:
            skipped.append({"invoice_id": invoice.get("id"), "reason": reason})
            continue

        if invoice.get("paid_date") is not None:
            continue

        action = _plan_action(invoice, sent_steps.get(invoice.get("id"), set()), today_date)
        if action is not None:
            actions.append(action)

    actions.sort(key=lambda action: action["invoice_id"])
    skipped.sort(key=lambda item: item["invoice_id"])
    return {"today": today, "actions": actions, "skipped": skipped}
