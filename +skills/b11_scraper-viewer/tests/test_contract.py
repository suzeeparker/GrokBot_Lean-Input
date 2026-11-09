"""Skill frontmatter, shared safety wording, and the absence of owner identifiers."""

from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]

REQUIRED = (
    "install",
    "uninstall",
    "explain",
    "do",
    "initial standalone",
    "Do not install silently",
    "public HTTP",
    "not bypassed",
    "metrics",
    "Unicode code points",
    "bytes, tokens",
    "raw HTML",
    "untrusted",
)


def frontmatter(text):
    if not text.startswith("---\n"):
        raise AssertionError("missing frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise AssertionError("unterminated frontmatter")
    data = {}
    for line in text[4:end].splitlines():
        key, value = line.split(":", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
            value = value[1:-1]
        data[key.strip()] = value
    return data


class ContractTests(unittest.TestCase):
    def test_frontmatter_and_shared_rules(self):
        bot = (ROOT / "+skills" / "b11_scraper-viewer" / "bot" / "SKILL.md").read_text(encoding="utf-8")
        mac = (ROOT / "+skills" / "b11_scraper-viewer" / "cursor" / "SKILL.md").read_text(encoding="utf-8")
        for text, folder in ((bot, "bot"), (mac, "cursor")):
            meta = frontmatter(text)
            self.assertEqual(meta["name"], "scraper-viewer")
            self.assertTrue(meta["description"])
            self.assertLess(len(meta["description"]), 1024)
            for phrase in REQUIRED:
                self.assertIn(phrase, text, folder)
        self.assertIn("$HOME/Tools/lean-input/output", bot)
        self.assertIn("$HOME/Tools/lean-input-bot/.venv/bin/python", bot)
        self.assertIn("Grok Bot skill library", bot)
        self.assertIn("active once the Bot can load it by name", bot)
        self.assertIn("shared by all of the owner's bots", bot)
        self.assertNotIn("Connect apps", bot)
        self.assertIn("/Users/Shared/Repos/GrokBot_/+data/DBMSs/JSONs/d11_scraper-viewer", mac)
        self.assertIn("d11_files.js", mac)
        self.assertIn("$HOME/Tools/lean-input/.venv/bin/python", mac)
        self.assertIn("$HOME/.cursor/skills/scraper-viewer", mac)
        self.assertIn("Customize", mac)
        self.assertIn("Sync Skills", mac)
        self.assertNotIn("lean-input-bot", mac)

    def test_shared_sources_have_no_owner_identifiers(self):
        roots = [
            ROOT / "+skills" / "b11_scraper-viewer",
            ROOT / "+skills" / "b10_lean_input",
            ROOT / "+skills" / "b00_packaging",
            ROOT / "+docs" / "B11_Scraper-Viewer",
            ROOT / "+docs" / "b10_Lean-Input",
            ROOT / "+docs" / "b12_Lean-Input-JQ",
        ]
        banned = ("@gmail.com", "suzee")
        for root in roots:
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix not in {".py", ".md", ".txt"}:
                    continue
                if "tests" in path.parts:
                    continue
                text = path.read_text(encoding="utf-8").lower()
                for needle in banned:
                    self.assertNotIn(needle, text, str(path))


if __name__ == "__main__":
    unittest.main()
