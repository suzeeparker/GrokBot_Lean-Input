"""Bot skill text. This file is not copied from the canonical suite."""

from __future__ import annotations

from pathlib import Path
import unittest

SKILL = Path(__file__).resolve().parents[1] / "SKILL.md"
TEXT = SKILL.read_text(encoding="utf-8")


class BotSkillTests(unittest.TestCase):
    def test_bot_skill_is_self_contained(self):
        self.assertIn("name: scraper-viewer", TEXT)
        self.assertIn("$HOME/Tools/lean-input-bot/scraper-viewer/scripts/", TEXT)
        self.assertNotIn("runtime/scraper-viewer", TEXT)
        self.assertNotIn("b10_lean_input", TEXT)
        self.assertIn("Grok Bot skill library", TEXT)
        self.assertIn("active once the Bot can load it by name", TEXT)
        self.assertIn("$HOME/Tools/lean-input/output", TEXT)
        self.assertLess(len(TEXT.split('description: "')[1].split('"')[0]), 1024)


if __name__ == "__main__":
    unittest.main()
