"""The owner's page: serve today's plan and record approve/reject decisions.

Run from inside python/:

    python app.py

Environment variables:
    PORT      port to listen on, default 8000
    DATA_DIR  folder with invoices.json and sent.json, default ../data
    TODAY     date as YYYY-MM-DD, default the real date
"""

import json
import os
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

from reminders import PlanError, build_plan
from reminders.page import render_error, render_page

PORT = int(os.environ.get("PORT", "8000"))
DATA_DIR = os.environ.get("DATA_DIR", "../data")
TODAY = os.environ.get("TODAY") or date.today().isoformat()

DECISIONS = {}


def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/index.html"):
            self.send_error(404)
            return
        body, status = self._load()
        self._send_html(body, status)

    def do_POST(self):
        if self.path != "/decide":
            self.send_error(404)
            return
        fields = self._form_fields()
        invoice_id = fields.get("invoice_id", "")
        decision = fields.get("decision", "")
        if invoice_id and decision in ("approved", "rejected"):
            DECISIONS[invoice_id] = decision
        self._redirect("/")

    def _load(self):
        try:
            invoices = read_json(os.path.join(DATA_DIR, "invoices.json"))
            sent = read_json(os.path.join(DATA_DIR, "sent.json"))
            plan = build_plan(invoices, sent, TODAY)
        except (OSError, json.JSONDecodeError) as error:
            return render_error(f"Could not read the data files: {error}"), 503
        except PlanError as error:
            return render_error(str(error)), 500
        return render_page(plan, invoices, DECISIONS), 200

    def _form_fields(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        return {key: values[0] for key, values in parse_qs(body).items()}

    def _send_html(self, body, status):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _redirect(self, location):
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()


def main():
    server = ThreadingHTTPServer(("", PORT), Handler)
    print(f"Serving on http://localhost:{PORT}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
