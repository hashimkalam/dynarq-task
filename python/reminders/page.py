"""Render the owner's page from a plan, the invoices and recorded decisions."""

from html import escape

from .messages import format_amount

REASON_TEXT = {
    "duplicate_id": "This invoice id appears more than once, so we could not tell "
    "which entry is correct.",
    "invalid_amount": "The amount is missing, not a number, or not greater than zero.",
    "missing_due_date": "The due date is missing.",
    "invalid_due_date": "The due date is not a real date in YYYY-MM-DD form.",
    "invalid_paid_date": "The paid date is not a real date, or it is in the future.",
}

STYLES = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body { margin: 0; font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  line-height: 1.5; }
main { max-width: 46rem; margin: 0 auto; padding: 1rem; }
h1 { font-size: 1.5rem; }
.card { border: 1px solid color-mix(in srgb, currentColor 20%, transparent);
  border-radius: 8px; padding: 1rem; margin: 0 0 1rem; }
dl { display: grid; grid-template-columns: max-content 1fr; gap: .25rem .75rem;
  margin: .5rem 0; }
dt { font-weight: 600; opacity: .7; }
dd { margin: 0; }
.message { white-space: pre-wrap; padding: .25rem 0 .25rem .75rem;
  border-left: 3px solid #888; }
.decide { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: .75rem; }
button { font: inherit; padding: .6rem 1rem; border-radius: 6px;
  border: 1px solid color-mix(in srgb, currentColor 35%, transparent);
  cursor: pointer; }
.decision { font-weight: 600; margin: .75rem 0 0; }
.note { opacity: .7; }
ul { padding-left: 1.25rem; }
"""


def _render_details(invoice, action):
    amount = format_amount(invoice["amount"], invoice["currency"])
    return (
        "<dl>"
        f"<dt>Invoice</dt><dd>{escape(str(action['invoice_id']))}</dd>"
        f"<dt>Amount</dt><dd>{escape(amount)}</dd>"
        f"<dt>Days overdue</dt><dd>{action['days_overdue']}</dd>"
        f"<dt>Step</dt><dd>{escape(action['step'])}</dd>"
        "</dl>"
    )


def _render_action(action, invoice, decisions):
    invoice_id = action["invoice_id"]
    customer = escape(str(invoice["customer"]))
    parts = [
        '<article class="card">',
        f"<h3>{customer}</h3>",
        _render_details(invoice, action),
        f'<p class="message">{escape(action["message"])}</p>',
    ]

    decision = decisions.get(invoice_id)
    if action["needs_approval"]:
        parts.append(
            '<form class="decide" method="post" action="/decide">'
            f'<input type="hidden" name="invoice_id" value="{escape(str(invoice_id))}">'
            '<button type="submit" name="decision" value="approved">Approve</button>'
            '<button type="submit" name="decision" value="rejected">Reject</button>'
            "</form>"
        )
        if decision:
            parts.append(
                f'<p class="decision" role="status">You {escape(decision)} this reminder.</p>'
            )
    else:
        parts.append('<p class="note">No approval needed for this reminder.</p>')

    parts.append("</article>")
    return "".join(parts)


def _render_skipped(skipped):
    if not skipped:
        return "<p class=\"note\">No invoices were skipped.</p>"
    items = []
    for entry in skipped:
        reason = REASON_TEXT.get(entry["reason"], entry["reason"])
        items.append(
            f"<li><strong>{escape(str(entry['invoice_id']))}</strong> — {escape(reason)}</li>"
        )
    return "<ul>" + "".join(items) + "</ul>"


def _page(title, body):
    return (
        "<!doctype html><html lang=\"en\"><head>"
        "<meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{escape(title)}</title>"
        f"<style>{STYLES}</style>"
        "</head><body><main>"
        f"{body}"
        "</main></body></html>"
    )


def render_page(plan, invoices, decisions):
    """Return the full owner's page as HTML."""
    by_id = {invoice.get("id"): invoice for invoice in invoices}

    if plan["actions"]:
        cards = "".join(
            _render_action(action, by_id[action["invoice_id"]], decisions)
            for action in plan["actions"]
        )
    else:
        cards = '<p class="note">Nothing to do today.</p>'

    body = (
        "<h1>Payment reminders</h1>"
        f'<p class="note">Today is <strong>{escape(plan["today"])}</strong>.</p>'
        "<section aria-labelledby=\"actions-heading\">"
        "<h2 id=\"actions-heading\">Today's plan</h2>"
        f"{cards}</section>"
        "<section aria-labelledby=\"skipped-heading\">"
        "<h2 id=\"skipped-heading\">Invoices we could not check</h2>"
        f"{_render_skipped(plan['skipped'])}</section>"
    )
    return _page("Payment reminders", body)


def render_error(message):
    """Return a friendly page for when the data cannot be read."""
    body = (
        "<h1>Payment reminders</h1>"
        "<p>We could not build today's plan.</p>"
        f'<p class="note">{escape(message)}</p>'
    )
    return _page("Payment reminders", body)
