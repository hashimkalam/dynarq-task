"""Reminder email text: one template per step.

Each message repeats only figures that come from the invoice: the amount and the
number of days overdue. No fees, interest, deadlines or earlier reminders appear.
"""

TEMPLATES = {
    "friendly": (
        "Dear {customer},\n\n"
        "We would like to gently remind you that invoice {invoice_id} for "
        "{amount}, which was due on {due_date}, is now {days_overdue} days overdue.\n\n"
        "If payment is already on its way, please ignore this message. Otherwise, "
        "we would be grateful if you could arrange payment at your earliest "
        "convenience.\n\n"
        "Kind regards,\nAccounts"
    ),
    "firm": (
        "Dear {customer},\n\n"
        "Our records show that invoice {invoice_id} for {amount}, due on "
        "{due_date}, is now {days_overdue} days overdue and remains unpaid.\n\n"
        "Please arrange payment without further delay. If there is a problem with "
        "this invoice, contact us so we can put it right.\n\n"
        "Regards,\nAccounts"
    ),
    "final": (
        "Dear {customer},\n\n"
        "Invoice {invoice_id} for {amount} was due on {due_date} and is now "
        "{days_overdue} days overdue. Payment has still not been received.\n\n"
        "Please treat this as a final notice and settle this invoice immediately, "
        "or contact us to discuss the matter.\n\n"
        "Regards,\nAccounts"
    ),
}


def format_amount(amount, currency):
    """Format an amount as '<currency> <value>' with exactly two decimals."""
    return f"{currency} {amount:.2f}"


def build_message(step, customer, invoice_id, due_date, amount, currency, days_overdue):
    """Render the reminder text for one step."""
    template = TEMPLATES[step]
    return template.format(
        customer=customer,
        invoice_id=invoice_id,
        due_date=due_date,
        amount=format_amount(amount, currency),
        days_overdue=days_overdue,
    )
