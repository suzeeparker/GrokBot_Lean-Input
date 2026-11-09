"""Staged installer tests under a temporary home directory."""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "+skills" / "b10_lean_input" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import install_runtime  # noqa: E402
from install_runtime import InstallError  # noqa: E402

PYTHON = "/usr/bin/python3"
REVISION = "test-revision"


def _fake_venv(path: Path):
    path.mkdir(parents=True)
    (path / "pyvenv.cfg").write_text("home = /usr\n", encoding="utf-8")
    python = path / "bin" / "python"
    python.parent.mkdir()
    python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    python.chmod(0o755)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self._python = install_runtime.probe_python
        self._trafilatura = install_runtime.probe_trafilatura
        self._pip = install_runtime.pip_install_pinned

    def tearDown(self):
        install_runtime.probe_python = self._python
        install_runtime.probe_trafilatura = self._trafilatura
        install_runtime.pip_install_pinned = self._pip

    def test_plan_without_approval_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            payload = install_runtime.install(home, "mac", ROOT, REVISION, PYTHON, approve=False)
            self.assertEqual(payload["approval"], "required")
            self.assertFalse((home / "Tools").exists())
            self.assertFalse((home / ".cursor").exists())

    def test_unmanaged_file_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            skill = install_runtime.destinations(home, "mac")["skill"]
            skill.parent.mkdir(parents=True)
            skill.write_text("user notes\n", encoding="utf-8")
            with self.assertRaises(InstallError) as caught:
                install_runtime.install(home, "mac", ROOT, REVISION, PYTHON, approve=True)
            self.assertIn("not owned", str(caught.exception))
            self.assertEqual(skill.read_text(encoding="utf-8"), "user notes\n")
            self.assertFalse(install_runtime.destinations(home, "mac")["runtime"].exists())

    def test_incompatible_preexisting_tool_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            venv = install_runtime.destinations(home, "bot")["venv"]
            _fake_venv(venv)
            install_runtime.probe_python = lambda _exe: (True, "3.12.3", "test")
            install_runtime.probe_trafilatura = lambda _exe: (True, "1.12.2", "")
            with self.assertRaises(InstallError) as caught:
                install_runtime.install(home, "bot", ROOT, REVISION, PYTHON, approve=True)
            self.assertIn("not upgraded", str(caught.exception))
            self.assertTrue((venv / "pyvenv.cfg").is_file())
            self.assertFalse(install_runtime.destinations(home, "bot")["runtime"].exists())

    def test_reuse_update_idempotence_and_confirmed_uninstall(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            dest = install_runtime.destinations(home, "mac")
            _fake_venv(dest["venv"])
            install_runtime.probe_python = lambda _exe: (True, "3.12.3", "test")
            install_runtime.probe_trafilatura = lambda _exe: (True, "2.2.0", "")

            def fail_pip(_python):
                raise AssertionError("pip should not run for a compatible preexisting install")

            install_runtime.pip_install_pinned = fail_pip
            first = install_runtime.install(home, "mac", ROOT, REVISION, PYTHON, approve=True)
            self.assertEqual(first["result"], "installed")
            self.assertEqual(first["dependency"]["ownership"], "preexisting-reused")
            self.assertEqual(first["dependency"]["version"], "2.2.0")
            self.assertIn("not changed", first["dependency"]["warning"])
            installed = dest["runtime"] / "extract_url.py"
            source = (SCRIPTS / "extract_url.py").read_bytes()
            self.assertEqual(installed.read_bytes(), source)
            skill_text = dest["skill"].read_text(encoding="utf-8")
            self.assertIn(".cursor/skills/lean-input-trafilatura", skill_text)
            notes = dest["skill"].parent / "notes.md"
            notes.write_text("unmanaged\n", encoding="utf-8")
            other = home / ".cursor" / "skills" / "other-skill" / "SKILL.md"
            other.parent.mkdir(parents=True)
            other.write_text("other\n", encoding="utf-8")
            mtimes = (installed.stat().st_mtime_ns, dest["skill"].stat().st_mtime_ns)
            second = install_runtime.install(home, "mac", ROOT, REVISION, PYTHON, approve=True)
            self.assertEqual(second["result"], "unchanged")
            self.assertEqual(mtimes, (installed.stat().st_mtime_ns, dest["skill"].stat().st_mtime_ns))
            installed.write_text("local edit\n", encoding="utf-8")
            with self.assertRaises(InstallError):
                install_runtime.install(home, "mac", ROOT, REVISION, PYTHON, approve=True)
            self.assertEqual(installed.read_text(encoding="utf-8"), "local edit\n")
            updated = install_runtime.install(home, "mac", ROOT, REVISION, PYTHON, approve=True, update=True)
            self.assertEqual(updated["result"], "updated")
            self.assertEqual(installed.read_bytes(), source)
            manifest = json.loads(dest["manifest"].read_text(encoding="utf-8"))
            self.assertEqual(manifest["source_revision"], REVISION)
            self.assertFalse(manifest["venv"]["managed"])
            blocked = install_runtime.uninstall(home, "mac", confirm="")
            self.assertEqual(blocked["result"], "confirmation-required")
            self.assertTrue(installed.is_file())
            removed = install_runtime.uninstall(home, "mac", confirm="YES")
            self.assertEqual(removed["result"], "removed")
            self.assertFalse(installed.exists())
            self.assertFalse(dest["skill"].exists())
            self.assertEqual(notes.read_text(encoding="utf-8"), "unmanaged\n")
            self.assertEqual(other.read_text(encoding="utf-8"), "other\n")
            self.assertTrue((dest["venv"] / "pyvenv.cfg").is_file())
            self.assertFalse(dest["manifest"].exists())

    def test_rollback_removes_files_and_new_venv(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()

            def boom(_python):
                raise InstallError("boom")

            install_runtime.pip_install_pinned = boom
            with self.assertRaises(InstallError):
                install_runtime.install(home, "bot", ROOT, REVISION, PYTHON, approve=True)
            self.assertFalse((home / "Tools").exists())

    def test_real_venv_install_is_idempotent_and_uninstall_keeps_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            first = install_runtime.install(home, "bot", ROOT, REVISION, PYTHON, approve=True)
            self.assertEqual(first["result"], "installed")
            self.assertEqual(first["dependency"]["version"], "2.3.1")
            self.assertEqual(first["dependency"]["ownership"], "installed-by-lean-input")
            python = Path(first["interpreter"])
            self.assertTrue(os.access(python, os.X_OK))
            mode = python.stat().st_mode
            self.assertTrue(mode & stat.S_IXUSR)
            probe = subprocess.run(
                [str(python), "-c", "import trafilatura; print(trafilatura.__version__)"],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(probe.stdout.strip(), "2.3.1")
            helper = install_runtime.destinations(home, "bot")["runtime"] / "extract_url.py"
            stamp = helper.stat().st_mtime_ns
            second = install_runtime.install(home, "bot", ROOT, REVISION, PYTHON, approve=True)
            self.assertEqual(second["result"], "unchanged")
            self.assertEqual(helper.stat().st_mtime_ns, stamp)
            output = home / "Tools" / "lean-input" / "output"
            output.mkdir(parents=True)
            (output / "kept.json").write_text("{}\n", encoding="utf-8")
            removed = install_runtime.uninstall(home, "bot", confirm="YES")
            self.assertEqual(removed["result"], "removed")
            self.assertFalse(helper.exists())
            self.assertEqual((output / "kept.json").read_text(encoding="utf-8"), "{}\n")
            probe = subprocess.run(
                [str(python), "-c", "import trafilatura; print(trafilatura.__version__)"],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(probe.stdout.strip(), "2.3.1")


if __name__ == "__main__":
    unittest.main()
