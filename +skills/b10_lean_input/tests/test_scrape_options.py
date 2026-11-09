"""Offline seo, aeo, and schema option tests. No network."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "+skills" / "b10_lean_input" / "scripts"))

import actions  # noqa: E402
import scrape_options as scrape  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def classify(text):
    _action, task = actions.parse_dispatch(text)
    option, rest = scrape.parse_scrape_option(task)
    return option, rest


def selected(text):
    _action, task = actions.parse_dispatch(text)
    return scrape.parse_options(task)


class ParserTests(unittest.TestCase):
    def test_options_are_standalone_tokens(self):
        parsed = selected("scrape seo https://example.com/a")
        self.assertEqual(parsed.options, ["seo"])
        self.assertEqual(parsed.task, "https://example.com/a")
        self.assertIsNone(parsed.error)
        parsed = selected("SCRAPE AEO https://example.com/a")
        self.assertEqual(parsed.options, ["aeo"])
        parsed = selected("do schema https://example.com/a")
        self.assertEqual(parsed.options, ["schema"])
        parsed = selected("scrape https://example.com/seo")
        self.assertEqual(parsed.options, ["page"])
        self.assertEqual(parsed.task, "https://example.com/seo")
        parsed = selected("scrape seoul.example")
        self.assertEqual(parsed.options, ["page"])
        self.assertEqual(parsed.task, "seoul.example")
        self.assertIsNone(parsed.error)
        parsed = selected("scraping https://example.com/a")
        self.assertIsNotNone(parsed.error)
        self.assertIn("Unknown option", parsed.error)

    def test_combinations_all_and_duplicates(self):
        parsed = selected("scrape schema seo https://example.com/a")
        self.assertEqual(parsed.options, ["seo", "schema"])
        parsed = selected("scrape page SEO aeo schema page https://example.com/a")
        self.assertEqual(parsed.options, ["page", "seo", "aeo", "schema"])
        parsed = selected("scrape all seo https://example.com/a")
        self.assertEqual(parsed.options, ["page", "seo", "aeo", "schema"])
        parsed = selected("scrape seo seo https://example.com/a")
        self.assertEqual(parsed.options, ["seo"])
        parsed = selected("do https://example.com/a")
        self.assertEqual(parsed.options, ["page"])
        parsed = selected("scrape foo https://example.com/a")
        self.assertIn("Unknown option 'foo'", parsed.error)
        parsed = selected("scrape seo")
        self.assertIn("URL is required", parsed.error)
        parsed = selected("scrape seo output /tmp/page.json https://example.com/a")
        self.assertEqual(parsed.options, ["seo"])
        self.assertEqual(parsed.task, "output /tmp/page.json https://example.com/a")
        parsed = selected("do extract https://example.com/a")
        self.assertIn("Unknown option 'extract'", parsed.error)
        parsed = selected("do scrape https://example.com/a")
        self.assertIn("Unknown option 'scrape'", parsed.error)


class ReportTests(unittest.TestCase):
    def test_robots_ai_crawlers_and_off_origin_sitemap(self):
        text = (FIXTURES / "robots_ai.txt").read_text(encoding="utf-8")
        self.assertEqual(scrape.crawler_directive(text, "GPTBot"), "blocked")
        self.assertEqual(scrape.crawler_directive(text, "Bingbot"), "allowed")
        self.assertEqual(scrape.crawler_directive(text, "ClaudeBot"), "not mentioned")

    def test_json_ld_graph_and_invalid_block(self):
        html = (FIXTURES / "schema_page.html").read_text(encoding="utf-8")
        page = scrape.parse_page(html)
        report = scrape.schema_report(page["json_ld_raw"], page["microdata"], page["rdfa"])
        self.assertEqual(report["json_ld_valid_count"], 1)
        self.assertIsInstance(report["json_ld_invalid"], list)
        self.assertIn("Organization", report["types_found"])
        self.assertIn("Article", report["types_found"])
        self.assertEqual(report["types"]["Organization"]["name"], "Garden Org")
        self.assertEqual(report["types"]["Product"], "not found")
        self.assertEqual(report["types"]["Article"]["dateModified"], "not found")
        self.assertEqual(report["microdata"], "present")
        self.assertEqual(page["canonical"], "not found")

    def test_seo_not_found_values_and_summary_without_network(self):
        html = (FIXTURES / "seo_page.html").read_text(encoding="utf-8")
        robots = (FIXTURES / "robots_ai.txt").read_text(encoding="utf-8")
        calls = []

        def fake(url, allow_tunnel=False, require_html=False, lock_origin=None):
            calls.append(url)
            if url.endswith("/garden"):
                return {"ok": True, "final_url": url, "http_status": 200, "text": html, "warnings": [], "error": None}
            if url.endswith("/robots.txt"):
                return {"ok": True, "final_url": url, "http_status": 200, "text": robots, "warnings": [], "error": None}
            if url.endswith("/sitemap.xml"):
                body = "<urlset><loc>https://example.com/garden</loc><loc>https://example.com/soil</loc></urlset>"
                return {"ok": True, "final_url": url, "http_status": 200, "text": body, "warnings": [], "error": None}
            if url.endswith("/llms.txt"):
                return {"ok": False, "final_url": url, "http_status": 404, "text": "", "warnings": [], "error": "HTTP status 404"}
            raise AssertionError(url)

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "page.seo.json"
            code, summary, written = scrape.run_selected(
                ["seo"], "https://example.com/garden", output, fetcher=fake,
            )
            self.assertEqual(code, 0)
            stored = __import__("json").loads(Path(written["seo"]["output"]).read_text(encoding="utf-8"))
        self.assertLessEqual(len(calls), scrape.MAX_FETCHES)
        self.assertEqual(len([item for item in calls if item.endswith("/garden")]), 1)
        self.assertNotIn("https://cdn.example.net/sitemap.xml", calls)
        self.assertIn("Meta description: How the garden grows", summary)
        self.assertIn("llms.txt: 404", summary)
        self.assertEqual(stored["page_meta"]["meta_robots"], "index,follow")
        self.assertEqual(stored["sitemap"]["url_count"], 2)
        self.assertEqual(stored["llms_txt"]["first_lines"], "not found")
        self.assertNotIn("keywords", stored)

    def test_localhost_writes_not_found_and_exits_2(self):
        def boom(*_args, **_kwargs):
            raise AssertionError("network")

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "page.aeo.json"
            code, summary, written = scrape.run_selected(["aeo"], "http://localhost/", output, fetcher=boom)
            stored = __import__("json").loads(Path(written["aeo"]["output"]).read_text(encoding="utf-8"))
        self.assertEqual(code, 2)
        self.assertIn("Localhost is forbidden", summary)
        self.assertEqual(stored["status"], "error")
        self.assertEqual(stored["checks"], [])

    def test_page_only_does_not_fetch_robots_sitemap_or_llms(self):
        html = (FIXTURES / "seo_page.html").read_text(encoding="utf-8")
        calls = []

        def fake(url, allow_tunnel=False, require_html=False, lock_origin=None):
            calls.append(url)
            return {"ok": True, "final_url": url, "http_status": 200, "text": html, "warnings": [], "error": None}

        with tempfile.TemporaryDirectory() as tmp:
            stem = Path(tmp) / "page-only.json"
            code, summary, written = scrape.run_selected(
                ["page"], "https://example.com/garden", stem, fetcher=fake,
            )
            stored = __import__("json").loads(Path(written["page"]["output"]).read_text(encoding="utf-8"))
        self.assertEqual(calls, ["https://example.com/garden"])
        self.assertEqual(set(stored), {
            "requested_url", "final_url", "title", "author", "publication_date",
            "text", "status", "warnings", "error",
        })
        self.assertIn("Page summary", summary)
        self.assertIn(written["page"]["output"], summary)
        self.assertTrue(written["page"]["output"].endswith("page-only.json"))
        self.assertIn(code, (0, 1))

    def test_several_options_fetch_the_page_once(self):
        html = (FIXTURES / "seo_page.html").read_text(encoding="utf-8")
        calls = []

        def fake(url, allow_tunnel=False, require_html=False, lock_origin=None):
            calls.append(url)
            if url.endswith("/garden"):
                return {"ok": True, "final_url": url, "http_status": 200, "text": html, "warnings": [], "error": None}
            if url.endswith("/robots.txt"):
                return {"ok": True, "final_url": url, "http_status": 200, "text": "User-agent: *\nAllow: /\n", "warnings": [], "error": None}
            if url.endswith("/llms.txt"):
                return {"ok": False, "final_url": url, "http_status": 404, "text": "", "warnings": [], "error": "HTTP status 404"}
            if url.endswith("/sitemap.xml"):
                return {"ok": False, "final_url": url, "http_status": 404, "text": "", "warnings": [], "error": "HTTP status 404"}
            raise AssertionError(url)

        with tempfile.TemporaryDirectory() as tmp:
            stem = Path(tmp) / "page-shared.json"
            code, summary, written = scrape.run_selected(
                ["page", "seo", "schema", "aeo"], "https://example.com/garden", stem, fetcher=fake,
            )
        self.assertEqual(len([item for item in calls if item.endswith("/garden")]), 1)
        self.assertEqual(len([item for item in calls if item.endswith("/robots.txt")]), 1)
        self.assertEqual(len([item for item in calls if item.endswith("/llms.txt")]), 1)
        self.assertLessEqual(len(calls), scrape.MAX_FETCHES)
        self.assertIn("page", written)
        self.assertTrue(written["page"]["output"].endswith("page-shared.json"))
        self.assertTrue(written["seo"]["output"].endswith("page-shared.seo.json"))
        self.assertTrue(written["aeo"]["output"].endswith("page-shared.aeo.json"))
        self.assertTrue(written["schema"]["output"].endswith("page-shared.schema.json"))
        self.assertIn("Page summary", summary)
        self.assertIn("SEO summary", summary)
        self.assertIn(written["seo"]["output"], summary)


if __name__ == "__main__":
    unittest.main()
