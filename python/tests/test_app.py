"""Integration tests for the web app over a real HTTP server."""

import http.client
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

import app

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


class AppTest(unittest.TestCase):
    def setUp(self):
        self.saved_dir = app.DATA_DIR
        self.saved_today = app.TODAY
        self.saved_decisions = dict(app.DECISIONS)
        self.had_log_message = "log_message" in app.Handler.__dict__
        self.saved_log_message = app.Handler.__dict__.get("log_message")

        app.DATA_DIR = str(DATA_DIR)
        app.TODAY = "2026-10-12"
        app.DECISIONS.clear()
        app.Handler.log_message = lambda *args, **kwargs: None

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        app.DATA_DIR = self.saved_dir
        app.TODAY = self.saved_today
        app.DECISIONS.clear()
        app.DECISIONS.update(self.saved_decisions)
        if self.had_log_message:
            app.Handler.log_message = self.saved_log_message
        else:
            del app.Handler.log_message

    def request(self, method, path, body=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {}
        if body is not None:
            body = body.encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        text = response.read().decode("utf-8")
        connection.close()
        return response.status, text

    def test_root_serves_the_plan(self):
        status, text = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("Alder Fabrication Ltd", text)
        self.assertIn("EUR 1250.00", text)

    def test_decision_is_recorded_and_shown(self):
        status, _ = self.request("POST", "/decide", "invoice_id=INV-1001&decision=approved")
        self.assertEqual(status, 303)
        _, text = self.request("GET", "/")
        self.assertIn("You approved this reminder.", text)

    def test_unknown_path_is_not_found(self):
        status, _ = self.request("GET", "/nope")
        self.assertEqual(status, 404)

    def test_unreadable_data_shows_a_friendly_page(self):
        app.DATA_DIR = str(DATA_DIR / "missing")
        status, text = self.request("GET", "/")
        self.assertEqual(status, 503)
        self.assertIn("We could not build today's plan.", text)


if __name__ == "__main__":
    unittest.main()
