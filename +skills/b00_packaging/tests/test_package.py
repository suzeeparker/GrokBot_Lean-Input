"""Candidate archives share one helper implementation and are not checkouts."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "+skills" / "b00_packaging" / "scripts"))
sys.path.insert(0, str(ROOT / "+skills" / "b10_lean_input" / "scripts"))

import build_candidates  # noqa: E402
import compare_candidates  # noqa: E402
import install_runtime  # noqa: E402

REVISION = "a" * 40


class PackageTests(unittest.TestCase):
    def test_archives_match_and_install_from_the_package_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            built = build_candidates.build(ROOT, REVISION, out)
            self.assertEqual(
                build_candidates.runtime_hashes(built["trees"]["bot"]),
                build_candidates.runtime_hashes(built["trees"]["mac"]),
            )
            bot_skill = (built["trees"]["bot"] / "SKILL.md").read_text(encoding="utf-8")
            mac_skill = (built["trees"]["mac"] / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("Grok Bot computer", bot_skill)
            self.assertIn("Cursor on this Mac", mac_skill)
            self.assertNotEqual(bot_skill, mac_skill)
            for archive in built["archives"].values():
                with zipfile.ZipFile(archive) as handle:
                    names = handle.namelist()
                self.assertTrue(names)
                self.assertFalse(any(".git" in name.split("/") for name in names))
            report = compare_candidates.compare(built["archives"]["bot"], built["archives"]["mac"])
            self.assertFalse(report["runtime_differs"])
            self.assertTrue(report["same_revision"])
            self.assertIn("SKILL.md", report["differing"])

            home = Path(tmp) / "home"
            package = built["trees"]["mac"]
            originals = (
                install_runtime.probe_python,
                install_runtime.probe_trafilatura,
                install_runtime.pip_install_pinned,
            )
            install_runtime.probe_python = lambda _exe: (True, "3.12.3", "test")
            install_runtime.probe_trafilatura = lambda _exe: (True, "2.3.1", "")

            def fail_pip(_exe):
                raise AssertionError("pip")

            install_runtime.pip_install_pinned = fail_pip
            venv = install_runtime.destinations(home, "mac")["venv"]
            venv.mkdir(parents=True)
            (venv / "pyvenv.cfg").write_text("home = /usr\n", encoding="utf-8")
            python = venv / "bin" / "python"
            python.parent.mkdir()
            python.write_text("#!/bin/sh\n", encoding="utf-8")
            python.chmod(0o755)
            try:
                result = install_runtime.install(home, "mac", package, None, "/usr/bin/python3", approve=True)
            finally:
                (
                    install_runtime.probe_python,
                    install_runtime.probe_trafilatura,
                    install_runtime.pip_install_pinned,
                ) = originals
            self.assertEqual(result["result"], "installed")
            self.assertEqual(result["source_revision"], REVISION)
            installed = install_runtime.destinations(home, "mac")["skill"].read_text(encoding="utf-8")
            self.assertEqual(installed, mac_skill)


if __name__ == "__main__":
    unittest.main()
