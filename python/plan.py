"""Command-line entry point for the payment reminder rules engine.

Run from inside python/:

    python plan.py --invoices ../data/invoices.json --sent ../data/sent.json \
        --today 2026-10-12 --out ../actions.json
"""

import argparse
import json
import sys

from reminders import PlanError, build_plan


def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_plan(path, plan):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(plan, handle, indent=2)
        handle.write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Plan today's payment reminders.")
    parser.add_argument("--invoices", required=True, help="path to invoices.json")
    parser.add_argument("--sent", required=True, help="path to sent.json")
    parser.add_argument("--today", required=True, help="date as YYYY-MM-DD")
    parser.add_argument("--out", required=True, help="path to write the plan JSON")
    args = parser.parse_args(argv)

    try:
        invoices = read_json(args.invoices)
        sent = read_json(args.sent)
        plan = build_plan(invoices, sent, args.today)
    except (OSError, json.JSONDecodeError) as error:
        print(f"Could not read input: {error}", file=sys.stderr)
        return 1
    except PlanError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    try:
        write_plan(args.out, plan)
    except OSError as error:
        print(f"Could not write plan: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
