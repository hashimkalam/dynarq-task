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
  --bg: #f4f5f7; --surface: #ffffff; --text: #16181d; --muted: #646b78;
  --border: #dfe2e8; --accent: #2f6fed; --ok: #1a7f4b; --danger: #c0362c;
  --friendly-fg: #2f6fed; --firm-fg: #9a5b00; --final-fg: #c0362c;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0e1013; --surface: #15181d; --text: #e7e9ee; --muted: #8b93a1;
    --border: #272b33; --accent: #6ea8fe; --ok: #3ecf8e; --danger: #f4716a;
    --friendly-fg: #6ea8fe; --firm-fg: #e0a94a; --final-fg: #f4716a;
  }
}
*, *::before, *::after { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text);
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  line-height: 1.5; -webkit-font-smoothing: antialiased; }
.wrap { max-width: 78rem; margin: 0 auto; padding: 1.5rem 1.5rem 3rem; }
header.top { display: flex; flex-wrap: wrap; gap: .25rem 1rem;
  align-items: baseline; justify-content: space-between;
  padding-bottom: 1rem; border-bottom: 1px solid var(--border); }
h1 { font-size: 1.2rem; font-weight: 650; letter-spacing: -.01em; margin: 0; }
.today { color: var(--muted); font-size: .85rem; margin: 0;
  font-variant-numeric: tabular-nums; }
.summary { display: flex; flex-wrap: wrap; gap: .35rem 1.1rem;
  margin: 1rem 0 1.75rem; color: var(--muted); font-size: .875rem; }
.summary span + span { padding-left: 1.1rem; border-left: 1px solid var(--border); }
.summary strong { color: var(--text); font-variant-numeric: tabular-nums; }
h2 { font-size: .78rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: .08em; color: var(--muted); margin: 2rem 0 .75rem; }
.cards { display: grid; gap: .75rem; align-items: start; grid-template-columns: 1fr; }
@media (min-width: 48rem) {
  .cards { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
.card { background: var(--surface); border: 1px solid var(--border);
  border-radius: 8px; padding: 1rem 1.15rem; margin: 0; }
.card__head { display: flex; gap: .75rem; align-items: center; justify-content: space-between; }
.card__title { margin: 0; font-size: 1rem; font-weight: 650; }
.badge { display: inline-flex; align-items: center; gap: .35rem; white-space: nowrap;
  font-size: .7rem; font-weight: 700; text-transform: uppercase; letter-spacing: .05em;
  padding: .18rem .5rem; border-radius: 6px; border: 1px solid currentColor; }
.badge::before { content: ""; width: .4rem; height: .4rem; border-radius: 50%;
  background: currentColor; }
.badge--friendly { color: var(--friendly-fg); }
.badge--firm { color: var(--firm-fg); }
.badge--final { color: var(--final-fg); }
.meta { display: grid; grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
  gap: .4rem 1.25rem; margin: .9rem 0 .25rem; font-size: .9rem; }
.meta div { display: flex; justify-content: space-between; gap: .5rem;
  border-bottom: 1px solid var(--border); padding-bottom: .3rem; }
.meta dt { color: var(--muted); }
.meta dd { margin: 0; font-weight: 600; font-variant-numeric: tabular-nums; }
.message { white-space: pre-wrap; margin: .9rem 0 0; padding: .8rem 1rem;
  border-radius: 6px; background: var(--bg); border: 1px solid var(--border);
  font-size: .9rem; }
.actions { display: flex; flex-wrap: wrap; gap: .5rem; align-items: center; margin-top: .9rem; }
.actions form { display: contents; }
button { font: inherit; font-weight: 600; font-size: .9rem; min-height: 44px;
  padding: .5rem 1.05rem; border-radius: 6px; border: 1px solid transparent;
  cursor: pointer; transition: background-color .12s ease, border-color .12s ease; }
button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.btn-approve { background: var(--ok); color: #fff; }
.btn-approve:hover { filter: brightness(.94); }
.btn-reject { background: transparent; color: var(--danger); border-color: var(--border); }
.btn-reject:hover { border-color: var(--danger); }
.decision { display: inline-flex; align-items: center; font-weight: 600; font-size: .85rem;
  margin: 0; padding: .3rem .6rem; border-radius: 6px;
  background: var(--bg); border: 1px solid var(--border); color: var(--muted); }
.note { color: var(--muted); font-size: .875rem; margin: .7rem 0 0; }
.empty { padding: 2.25rem 1rem; text-align: center; color: var(--muted);
  background: var(--surface); border: 1px solid var(--border); border-radius: 8px; }
.empty strong { display: block; color: var(--text); font-weight: 650; margin-bottom: .2rem; }
ul.skipped { list-style: none; padding: 0; margin: 0; }
ul.skipped li { padding: .6rem .1rem; font-size: .875rem; color: var(--muted);
  border-top: 1px solid var(--border); }
ul.skipped strong { color: var(--text); font-weight: 600; }
"""


def _render_summary(plan):
    to_do = len(plan["actions"])
    approvals = sum(1 for action in plan["actions"] if action["needs_approval"])
    skipped = len(plan["skipped"])
    return (
        '<p class="summary">'
        f"<span><strong>{to_do}</strong> to do</span>"
        f"<span><strong>{approvals}</strong> need approval</span>"
        f"<span><strong>{skipped}</strong> skipped</span>"
        "</p>"
    )


def _render_action(action, invoice, decisions):
    invoice_id = action["invoice_id"]
    step = escape(action["step"])
    customer = escape(str(invoice.get("customer", "")))
    amount = escape(format_amount(invoice["amount"], invoice["currency"]))

    parts = [
        '<article class="card">',
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
        cards = '<div class="cards">' + "".join(
            _render_action(action, by_id[action["invoice_id"]], decisions)
            for action in plan["actions"]
        ) + "</div>"
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
