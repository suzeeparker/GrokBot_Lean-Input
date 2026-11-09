"""macOS skill text. This file is not copied from the canonical suite."""

from __future__ import annotations

from pathlib import Path
import unittest

SKILL = Path(__file__).resolve().parents[1] / "SKILL.md"
TEXT = SKILL.read_text(encoding="utf-8")


class MacSkillTests(unittest.TestCase):
    def test_mac_skill_is_self_contained(self):
        self.assertIn("name: scraper-viewer", TEXT)
        self.assertIn("macOS", TEXT)
        self.assertIn("$HOME/.cursor/skills/scraper-viewer/scripts/", TEXT)
        self.assertIn("/Users/Shared/Repos/GrokBot_/+data/DBMSs/JSONs/d11_scraper-viewer", TEXT)
        self.assertIn("d11_files.js", TEXT)
        self.assertIn("Customize", TEXT)
        self.assertIn("Sync Skills", TEXT)
        self.assertNotIn("lean-input-bot", TEXT)
        self.assertNotIn("runtime/scraper-viewer", TEXT)
        self.assertNotIn("b10_lean_input", TEXT)
        self.assertLess(len(TEXT.split('description: "')[1].split('"')[0]), 1024)


if __name__ == "__main__":
    unittest.main()
