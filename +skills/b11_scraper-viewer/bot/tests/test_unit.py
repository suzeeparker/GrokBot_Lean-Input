"""Stdlib contract tests. Injected extractors do not certify Trafilatura."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[1]
SCRIPTS = PACKAGE / "scripts"
sys.path.insert(0, str(SCRIPTS))

import extract_url as m  # noqa: E402


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        status, content_type, body = self.server.queue.pop(0)
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, _fmt, *_args):
        return


class UnitTests(unittest.TestCase):
    def test_url_rejections_do_not_resolve(self):
        def fail_lookup(*_args, **_kwargs):
            raise AssertionError("DNS should not be called")

        urls = (
            "file:///etc/passwd",
            "http://localhost/",
            "http://localhost./",
            "https://user:pass@example.org",
            "http://example.org:8080",
            "https://example.org/\nX",
            "http://127.0.0.1/",
            "http://[::1]/",
            "ftp://example.org/",
        )
        with patch.object(m.socket, "getaddrinfo", fail_lookup):
            for url in urls:
                with self.subTest(url=url):
                    with self.assertRaises(ValueError):
                        m.validate_url(url)

    def test_private_dns(self):
        for address in ("127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "100.64.0.1"):
            with patch.object(m.socket, "getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 80))]):
                with self.assertRaises(ValueError):
                    m.public_addresses("example.org", 80)

    def test_bot_egress_tunnel_is_narrow(self):
        tunnel = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("198.18.0.1", 443))]
        mixed = tunnel + [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.1.2.3", 443))]
        with patch.dict(os.environ, {m.TUNNEL_ENV: "127.0.0.1:8791"}):
            with patch.object(m.socket, "getaddrinfo", return_value=tunnel):
                accepted = m.public_addresses("example.com", 443, allow_tunnel=True)
                self.assertTrue(m.resolved_uses_tunnel(accepted))
            with patch.object(m.socket, "getaddrinfo", return_value=tunnel):
                with self.assertRaises(ValueError):
                    m.public_addresses("example.com", 443, allow_tunnel=False)
            with patch.object(m.socket, "getaddrinfo", return_value=mixed):
                with self.assertRaises(ValueError):
                    m.public_addresses("example.com", 443, allow_tunnel=True)
        cleaned = os.environ.copy()
        cleaned.pop(m.TUNNEL_ENV, None)
        with patch.dict(os.environ, cleaned, clear=True):
            with patch.object(m.socket, "getaddrinfo", return_value=tunnel):
                with self.assertRaises(ValueError):
                    m.public_addresses("example.com", 443, allow_tunnel=True)
        with patch.object(m.socket, "getaddrinfo", side_effect=AssertionError("DNS should not be called")):
            with self.assertRaises(ValueError):
                m.validate_url("https://198.18.0.1/")

    def test_tunnel_warning_uses_original_host(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.queue = [(200, "text/html; charset=utf-8", "<html><body>ok</body></html>")]
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.shutdown)
        self.addCleanup(server.server_close)

        def fake_dns(_host, _port, type=0):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("198.18.0.1", port))]

        real_connect = socket.socket.connect

        def connect(sock, address):
            return real_connect(sock, ("127.0.0.1", port))

        with patch.dict(os.environ, {m.TUNNEL_ENV: "127.0.0.1:8791"}):
            with patch.object(m.socket, "getaddrinfo", fake_dns):
                with patch.object(socket.socket, "connect", connect):
                    html, final, warnings = m.fetch_html("http://example.com/page", allow_tunnel=True)
        self.assertIn("ok", html)
        self.assertEqual(final, "http://example.com/page")
        self.assertTrue(any("egress tunnel" in item for item in warnings))

    def test_redirect_rules(self):
        with self.assertRaises(ValueError):
            m.next_hop("https://example.org/a", "http://example.org/b", "https")
        with self.assertRaises(ValueError):
            m.next_hop("https://example.org/a", "file:///etc/passwd", "https")
        cleaned = m.next_hop("https://example.org/dir/a", "/next#frag", "https")
        self.assertEqual(cleaned, "https://example.org/next")
        self.assertRaises(ValueError, m.public_addresses, "127.0.0.1", 80)

    def test_contract_counts_and_unicode_roundtrip(self):
        html = "<html><body>café</body></html>"

        def fake_extract(_html, _url):
            return {
                "title": None,
                "author": None,
                "publication_date": None,
                "text": "café",
                "warnings": ["kept"],
            }

        result, original = m.process("https://example.org/a", lambda _url: (html, "https://example.org/a", []), fake_extract)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["text"], "café")
        self.assertNotIn("serialized_json_characters", result)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out.json"
            metrics = m.write_outputs(result, output, original, True)
            written = output.read_text(encoding="utf-8")
            self.assertEqual(metrics["decoded_html_characters"], len(html))
            self.assertEqual(metrics["extracted_text_characters"], 4)
            self.assertEqual(metrics["serialized_json_characters"], len(written))
            self.assertEqual(metrics["unit"], "unicode_code_points")
            loaded = json.loads(written)
            self.assertEqual(loaded["text"], "café")
            self.assertIn("café", written)
            self.assertNotIn("serialized_json_characters", loaded)
            self.assertEqual((output.with_suffix(".source.html")).read_text(encoding="utf-8"), html)
            with self.assertRaises(FileExistsError):
                m.write_outputs(result, output, original, False)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["text"], "café")

    def test_sidecar_collision_preserves_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out.json"
            sidecar = output.with_suffix(".metrics.json")
            sidecar.write_text("existing", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                m.write_outputs({"text": "x", "status": "success"}, output, "<html></html>", False)
            self.assertFalse(output.exists())
            self.assertEqual(sidecar.read_text(encoding="utf-8"), "existing")

    def test_network_and_empty_failures_keep_null_text(self):
        def broken(_url):
            raise TimeoutError("mock timeout")

        result, html = m.process("https://example.org/a", broken)
        self.assertEqual(result["status"], "error")
        self.assertIsNone(html)
        self.assertIsNone(result["text"])
        self.assertIn("timeout", result["error"].lower())

        def empty(_html, _url):
            raise ValueError("Empty extraction")

        result, html = m.process("https://example.org/a", lambda _url: ("<html/>", "https://example.org/a", []), empty)
        self.assertEqual(result["status"], "error")
        self.assertIsNone(result["text"])
        self.assertEqual(html, "<html/>")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "err.json"
            metrics = m.write_outputs(result, output, html, False)
            self.assertEqual(metrics["decoded_html_characters"], len("<html/>"))
            self.assertIsNone(metrics["extracted_text_characters"])

    def test_local_http_status_and_content_type(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.queue = [
            (404, "text/html; charset=utf-8", "<html>missing</html>"),
            (200, "text/plain; charset=utf-8", "not html"),
            (200, "text/html; charset=utf-8", "<html><body>café</body></html>"),
        ]
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.shutdown)
        self.addCleanup(server.server_close)

        def fake_public(_host, _port, allow_tunnel=False):
            return socket.getaddrinfo("127.0.0.1", port, type=socket.SOCK_STREAM)

        with patch.object(m, "public_addresses", fake_public):
            with self.assertRaises(ValueError) as caught:
                m.fetch_html("http://example.org/missing")
            self.assertIn("404", str(caught.exception))
            with self.assertRaises(ValueError) as caught:
                m.fetch_html("http://example.org/plain")
            self.assertIn("not HTML", str(caught.exception))
            html, final, warnings = m.fetch_html("http://example.org/page")
        self.assertEqual(final, "http://example.org/page")
        self.assertIn("café", html)
        self.assertEqual(warnings, [])

    def test_cli_private_url_writes_error_without_html_on_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["HOME"] = tmp
            output = Path(tmp) / "out.json"
            proc = subprocess.run(
                [sys.executable, str(SCRIPTS / "extract_url.py"), "http://127.0.0.1/", "--output", str(output)],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            self.assertEqual(proc.returncode, 2)
            self.assertNotIn("<html", proc.stdout)
            summary = json.loads(proc.stdout)
            self.assertEqual(summary["status"], "error")
            loaded = json.loads(output.read_text(encoding="utf-8"))
            self.assertIsNone(loaded["text"])
            self.assertIsNone(summary["metrics"]["decoded_html_characters"])
            sidecar = json.loads(output.with_suffix(".metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(sidecar["serialized_json_characters"], len(output.read_text(encoding="utf-8")))

    def test_cli_localhost_refusal_exits_2_and_fetch_failure_exits_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            refused = Path(tmp) / "localhost.json"
            code = m.main(["http://localhost/", "--output", str(refused)])
            self.assertEqual(code, 2)
            loaded = json.loads(refused.read_text(encoding="utf-8"))
            self.assertEqual(loaded["status"], "error")
            self.assertIn("Localhost is forbidden", loaded["error"])
            self.assertIsNone(loaded["text"])
            fetched = Path(tmp) / "fetch.json"

            def fail_fetch(_url, allow_tunnel=False):
                raise ValueError("Nonpublic destination rejected")

            with patch.object(m, "fetch_html", fail_fetch):
                code = m.main(["https://example.com/article", "--output", str(fetched)])
            self.assertEqual(code, 1)
            loaded = json.loads(fetched.read_text(encoding="utf-8"))
            self.assertIn("Nonpublic destination rejected", loaded["error"])


if __name__ == "__main__":
    unittest.main()
