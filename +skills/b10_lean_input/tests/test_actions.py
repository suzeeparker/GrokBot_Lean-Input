"""Action-word parsing and read-only or missing-runtime dispatch."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "+skills" / "b10_lean_input" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import actions  # noqa: E402
import install_runtime  # noqa: E402


class ParseTests(unittest.TestCase):
    def test_initial_word_only(self):
        cases = {
            "install": ("install", ""),
            "Install": ("install", ""),
            "uninstall please": ("uninstall", "please"),
            "explain": ("explain", ""),
            "do extract https://example.com": ("do", "extract https://example.com"),
            "https://example.com/a": ("do", "https://example.com/a"),
            "extract https://example.com": ("do", "extract https://example.com"),
            "lean-input-trafilatura install": ("install", ""),
            "# lean-input-trafilatura explain": ("explain", ""),
            "lean-input-trafilatura https://example.com": ("do", "https://example.com"),
            "installing packages": ("do", "installing packages"),
            "do": ("do", ""),
            "  explain  ": ("explain", ""),
            "do install": ("do", "install"),
            "install,": ("do", "install,"),
            "": ("do", ""),
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(actions.parse_dispatch(text), expected)

    def test_task_url_output_and_retention(self):
        urls, output, retain = actions.parse_task(
            'extract https://example.com/a. output "/tmp/my file.json" retain html extra https://example.org/b'
        )
        self.assertEqual(urls, ["https://example.com/a", "https://example.org/b"])
        self.assertEqual(output, "/tmp/my file.json")
        self.assertTrue(retain)


class DispatchTests(unittest.TestCase):
    def test_explain_makes_no_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            before = list(Path(tmp).rglob("*"))
            code = actions.dispatch("explain the output", home, "mac")
            self.assertEqual(code, 0)
            self.assertEqual(list(Path(tmp).rglob("*")), before)
            self.assertFalse(home.exists())

    def test_do_offers_setup_without_installing(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            code = actions.dispatch("https://example.com/", home, "bot")
            self.assertEqual(code, 10)
            self.assertFalse((home / "Tools").exists())

    def test_do_without_url_does_not_fetch(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            runtime = install_runtime.destinations(home, "mac")["runtime"]
            runtime.mkdir(parents=True)
            (runtime / "extract_url.py").write_text("# placeholder\n", encoding="utf-8")
            python = install_runtime.destinations(home, "mac")["venv"] / "bin" / "python"
            python.parent.mkdir(parents=True)
            python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            python.chmod(0o755)
            code = actions.dispatch("do install", home, "mac")
            self.assertEqual(code, 2)

    def test_uninstall_without_manifest_removes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            marker = home / "keep.txt"
            marker.write_text("keep", encoding="utf-8")
            code = actions.dispatch("uninstall", home, "mac", confirm="YES")
            self.assertEqual(code, 0)
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep")

    def test_cli_explain_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "actions.py"),
                    "--message",
                    "explain",
                    "--target",
                    "bot",
                    "--home",
                    str(Path(tmp) / "absent"),
                ],
                capture_output=True,
                text=True,
                check=False,
                env={**os.environ, "HOME": tmp},
            )
            self.assertEqual(proc.returncode, 0)
            self.assertIn("did not change files", proc.stdout)
            self.assertFalse((Path(tmp) / "absent").exists())


if __name__ == "__main__":
    unittest.main()
