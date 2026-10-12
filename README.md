# Payment reminder assistant (Python)

Rules engine, owner's page and reminder messages for chasing unpaid invoices.

## Run

From inside `python/`:

- Tests: `python -m unittest`
- Plan: `python plan.py --invoices ../data/invoices.json --sent ../data/sent.json --today 2026-10-12 --out ../actions.json`
- Page: `python app.py`, then open http://localhost:8000/

The page reads `PORT` (default 8000), `DATA_DIR` (default `../data`) and `TODAY`
(default the real date). Standard library only: no install, no internet.

## Structure and decisions

- `reminders/` holds the logic: `dates.py` (strict `YYYY-MM-DD` parsing),
  `engine.py` (skip precedence, steps, sent-suppression), `messages.py` (templates)
  and `page.py` (HTML). `plan.py` and `app.py` are thin entry points, and the page
  calls the same `build_plan`, so the rules live in one place.
- Skipped invoices report the first reason in README order; duplicates are listed
  once; both output lists are sorted by id in plain text order.
- Messages come from templates (no fees, interest or extra figures) and need no API
  key, so everything works offline. Decisions are kept in memory while the app runs.

## Next with more time

Persist decisions, send the emails for real, and load Part 4's rate/fee wording from
configuration once it has been legally checked.
