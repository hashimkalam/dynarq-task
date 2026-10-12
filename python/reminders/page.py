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
:root {
  --bg: #eef1f6; --surface: #ffffff; --text: #141821; --muted: #5b6472;
  --border: #dde2ea; --primary: #4f46e5; --ok: #137a4b; --danger: #c02b2b;
  --friendly-bg: #e0edff; --friendly-fg: #1d4ed8;
  --firm-bg: #fff0d4; --firm-fg: #9a5b00;
  --final-bg: #ffe1e1; --final-fg: #b91c1c;
  --shadow: 0 1px 2px rgba(16, 24, 40, .06), 0 1px 3px rgba(16, 24, 40, .1);
  --radius: 14px;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0d1016; --surface: #161a22; --text: #e8ebf0; --muted: #98a2b3;
    --border: #262c37; --primary: #818cf8; --ok: #34d399; --danger: #f87171;
    --friendly-bg: #17233c; --friendly-fg: #93c5fd;
    --firm-bg: #3a2c10; --firm-fg: #fcd34d;
    --final-bg: #3a1616; --final-fg: #fca5a5;
    --shadow: none;
  }
}
*, *::before, *::after { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text);
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  line-height: 1.55; -webkit-font-smoothing: antialiased; }
.wrap { max-width: 42rem; margin: 0 auto; padding: 1.25rem; }
header.top { display: flex; flex-wrap: wrap; gap: .25rem 1rem;
  align-items: baseline; justify-content: space-between; }
h1 { font-size: 1.35rem; letter-spacing: -.01em; margin: 0; }
.today { color: var(--muted); font-size: .9rem; margin: 0; }
.summary { display: flex; flex-wrap: wrap; gap: .5rem; margin: 1rem 0 1.25rem; }
.summary span { font-size: .82rem; font-weight: 600; padding: .3rem .7rem;
  border-radius: 999px; background: var(--surface); border: 1px solid var(--border);
  color: var(--muted); }
h2 { font-size: .95rem; text-transform: uppercase; letter-spacing: .06em;
  color: var(--muted); margin: 1.75rem 0 .75rem; }
.card { background: var(--surface); border: 1px solid var(--border);
  border-left: 4px solid var(--border); border-radius: var(--radius);
  box-shadow: var(--shadow); padding: 1rem 1.1rem; margin-bottom: 1rem; }
.card--friendly { border-left-color: var(--friendly-fg); }
.card--firm { border-left-color: var(--firm-fg); }
.card--final { border-left-color: var(--final-fg); }
.card__head { display: flex; gap: .75rem; align-items: center; justify-content: space-between; }
.card__title { margin: 0; font-size: 1.05rem; }
.badge { font-size: .72rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: .04em; padding: .2rem .55rem; border-radius: 999px; white-space: nowrap; }
.badge--friendly { background: var(--friendly-bg); color: var(--friendly-fg); }
.badge--firm { background: var(--firm-bg); color: var(--firm-fg); }
.badge--final { background: var(--final-bg); color: var(--final-fg); }
.meta { display: grid; grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
  gap: .5rem 1rem; margin: .85rem 0 .25rem; }
.meta div { display: flex; justify-content: space-between; gap: .5rem;
  border-bottom: 1px dashed var(--border); padding-bottom: .35rem; }
.meta dt { color: var(--muted); font-size: .85rem; }
.meta dd { margin: 0; font-weight: 600; font-variant-numeric: tabular-nums; }
.message { white-space: pre-wrap; margin: .75rem 0 0; padding: .75rem .9rem;
  border-radius: 10px; background: var(--bg); border: 1px solid var(--border);
  font-size: .92rem; }
.actions { display: flex; flex-wrap: wrap; gap: .5rem; align-items: center; margin-top: .9rem; }
.actions form { display: contents; }
button { font: inherit; font-weight: 600; min-height: 44px; padding: .5rem 1.1rem;
  border-radius: 10px; border: 1px solid transparent; cursor: pointer;
  transition: filter .15s ease; }
button:hover { filter: brightness(1.05); }
button:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.btn-approve { background: var(--ok); color: #fff; }
.btn-reject { background: transparent; color: var(--danger); border-color: currentColor; }
.decision { display: inline-flex; align-items: center; gap: .4rem; font-weight: 700;
  font-size: .9rem; margin: 0; padding: .3rem .7rem; border-radius: 999px;
  background: var(--bg); border: 1px solid var(--border); }
.note { color: var(--muted); font-size: .9rem; margin: .6rem 0 0; }
.empty { text-align: center; padding: 2rem 1rem; color: var(--muted);
  background: var(--surface); border: 1px dashed var(--border); border-radius: var(--radius); }
.empty strong { display: block; color: var(--text); font-size: 1.05rem; margin-bottom: .25rem; }
ul.skipped { list-style: none; padding: 0; margin: 0; display: grid; gap: .5rem; }
ul.skipped li { background: var(--surface); border: 1px solid var(--border);
  border-radius: 10px; padding: .6rem .8rem; font-size: .9rem; color: var(--muted); }
ul.skipped strong { color: var(--text); }
"""


def _render_summary(plan):
    to_do = len(plan["actions"])
    approvals = sum(1 for action in plan["actions"] if action["needs_approval"])
    skipped = len(plan["skipped"])
    return (
        '<div class="summary">'
        f"<span>{to_do} to do</span>"
        f"<span>{approvals} need approval</span>"
        f"<span>{skipped} skipped</span>"
        "</div>"
    )


def _render_action(action, invoice, decisions):
    invoice_id = action["invoice_id"]
    step = escape(action["step"])
    customer = escape(str(invoice.get("customer", "")))
    amount = escape(format_amount(invoice["amount"], invoice["currency"]))

    parts = [
        f'<article class="card card--{step}">',
        '<div class="card__head">',
        f'<h3 class="card__title">{customer}</h3>',
        f'<span class="badge badge--{step}">{step}</span>',
        "</div>",
        '<dl class="meta">',
        f'<div><dt>Invoice</dt><dd>{escape(str(invoice_id))}</dd></div>',
        f"<div><dt>Amount</dt><dd>{amount}</dd></div>",
        f'<div><dt>Days overdue</dt><dd>{action["days_overdue"]}</dd></div>',
        "</dl>",
        f'<p class="message">{escape(action["message"])}</p>',
        '<div class="actions">',
    ]

    decision = decisions.get(invoice_id)
    if action["needs_approval"]:
        parts.append(
            '<form method="post" action="/decide">'
            f'<input type="hidden" name="invoice_id" value="{escape(str(invoice_id))}">'
            '<button type="submit" class="btn-approve" name="decision" value="approved">Approve</button>'
            '<button type="submit" class="btn-reject" name="decision" value="rejected">Reject</button>'
            "</form>"
        )
        if decision:
            parts.append(
                f'<p class="decision" role="status">You {escape(decision)} this reminder.</p>'
            )
    else:
        parts.append('<p class="note">No approval needed for this reminder.</p>')

    parts += ["</div>", "</article>"]
    return "".join(parts)


def _render_skipped(skipped):
    if not skipped:
        return '<p class="note">No invoices were skipped.</p>'
    items = []
    for entry in skipped:
        reason = REASON_TEXT.get(entry["reason"], entry["reason"])
        items.append(
            f"<li><strong>{escape(str(entry['invoice_id']))}</strong> — {escape(reason)}</li>"
        )
    return '<ul class="skipped">' + "".join(items) + "</ul>"


def _page(title, body):
    return (
        '<!doctype html><html lang="en"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="color-scheme" content="light dark">'
        f"<title>{escape(title)}</title>"
        f"<style>{STYLES}</style>"
        "</head><body>"
        f"{body}"
        "</body></html>"
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
        cards = (
            '<div class="empty"><strong>Nothing to do today.</strong>'
            "<span>No reminders are due right now.</span></div>"
        )

    body = (
        '<div class="wrap">'
        '<header class="top">'
        "<h1>Payment reminders</h1>"
        f'<p class="today">Today is <time datetime="{escape(plan["today"])}">'
        f'{escape(plan["today"])}</time></p>'
        "</header>"
        f"{_render_summary(plan)}"
        "<main>"
        '<section aria-labelledby="actions-heading">'
        "<h2 id=\"actions-heading\">Today's plan</h2>"
        f"{cards}"
        "</section>"
        '<section aria-labelledby="skipped-heading">'
        '<h2 id="skipped-heading">Invoices we could not check</h2>'
        f"{_render_skipped(plan['skipped'])}"
        "</section>"
        "</main>"
        "</div>"
    )
    return _page("Payment reminders", body)


def render_error(message):
    """Return a friendly page for when the data cannot be read."""
    body = (
        '<div class="wrap"><main>'
        "<h1>Payment reminders</h1>"
        '<div class="card">'
        "<p>We could not build today's plan.</p>"
        f'<p class="note">{escape(message)}</p>'
        "</div>"
        "</main></div>"
    )
    return _page("Payment reminders", body)
