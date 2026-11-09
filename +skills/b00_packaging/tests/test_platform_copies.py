"""Delivered platform folders match the canonical helper source."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "+skills" / "b10_lean_input" / "scripts"))

from constants import RUNTIME_FILES  # noqa: E402

CANON = ROOT / "+skills" / "b10_lean_input" / "scripts"
DOCS = ROOT / "+docs" / "b11_Scraper-Viewer"


class CopyTests(unittest.TestCase):
    def test_shared_scripts_match_and_win_is_absent(self):
        self.assertFalse((ROOT / "+skills" / "b11_scraper-viewer" / "win").exists())
        for platform in ("bot", "mac"):
            folder = ROOT / "+skills" / "b11_scraper-viewer" / platform
            self.assertTrue((folder / "SKILL.md").is_file(), platform)
            self.assertTrue((folder / "scripts" / "run.py").is_file(), platform)
            self.assertTrue((folder / "docs" / "Onboarding.md").is_file(), platform)
            self.assertTrue((folder / "tests" / "test_install.py").is_file(), platform)
            for name in RUNTIME_FILES:
                delivered = (folder / "scripts" / name).read_bytes()
                self.assertEqual(delivered, (CANON / name).read_bytes(), f"{platform}/{name}")
            for path in DOCS.glob("*.md"):
                copy = folder / "docs" / path.name
                self.assertEqual(copy.read_bytes(), path.read_bytes(), f"{platform}/{path.name}")
            text = (folder / "scripts" / "run.py").read_text(encoding="utf-8")
            self.assertNotIn("b10_lean_input", text)


if __name__ == "__main__":
    unittest.main()
