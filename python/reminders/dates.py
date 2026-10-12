"""Strict date parsing and overdue arithmetic."""

import re
from datetime import date

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_date(value):
    """Return a date for a strict YYYY-MM-DD string, otherwise None."""
    if not isinstance(value, str) or not _DATE_PATTERN.match(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def days_overdue(today, due):
    """Calendar days from due to today, counting a due date of today as 0."""
    return (today - due).days
