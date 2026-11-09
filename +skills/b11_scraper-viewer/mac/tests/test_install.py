"""Staged installer tests under a temporary home directory."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

PACKAGE = Path(__file__).resolve().parents[1]
SCRIPTS = PACKAGE / "scripts"
sys.path.insert(0, str(SCRIPTS))


def repo_root():
    for parent in PACKAGE.parents:
        if (parent / "CONTRIBUTING.md").is_file() and (parent / "+skills").is_dir():
            return parent
    raise AssertionError("repository root not found")


def package_target():
    """Return bot or mac when this tree is one platform package, else None.

    A shipped archive is not named bot or mac. Its CANDIDATE.json and run.py
    name the platform. The canonical b10 tree has neither and runs both.
    """
    candidate = PACKAGE / "CANDIDATE.json"
    if candidate.is_file():
        try:
            recorded = json.loads(candidate.read_text(encoding="utf-8")).get("target")
        except (OSError, json.JSONDecodeError):
            recorded = None
        if recorded in {"bot", "mac"}:
            return recorded
    run_py = PACKAGE / "scripts" / "run.py"
    if run_py.is_file():
        text = run_py.read_text(encoding="utf-8")
        for name in ("bot", "mac"):
            if f'PLATFORM = "{name}"' in text:
                return name
    if PACKAGE.name in {"bot", "mac"}:
        return PACKAGE.name
    return None


def install_source(target):
    """Use this platform folder when it is a self-contained skill, else the repo."""
    own = package_target()
    if (PACKAGE / "SKILL.md").is_file() and own is not None:
        if own != target:
            return None
        return PACKAGE
    return repo_root()


def source_for(target):
    source = install_source(target)
    if source is None:
        raise unittest.SkipTest(f"{package_target() or PACKAGE.name} does not install the {target} target")
    return source


def revision_for(source):
    """Use the archive revision when CANDIDATE.json is present."""
    candidate = Path(source) / "CANDIDATE.json"
    if candidate.is_file():
        return json.loads(candidate.read_text(encoding="utf-8"))["source_revision"]
    return "test-revision"

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
            payload = install_runtime.install(home, "mac", source_for("mac"), revision_for(source_for("mac")), PYTHON, approve=False)
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
                install_runtime.install(home, "mac", source_for("mac"), revision_for(source_for("mac")), PYTHON, approve=True)
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
                install_runtime.install(home, "bot", source_for("bot"), revision_for(source_for("bot")), PYTHON, approve=True)
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
            first = install_runtime.install(home, "mac", source_for("mac"), revision_for(source_for("mac")), PYTHON, approve=True)
            self.assertEqual(first["result"], "installed")
            self.assertEqual(first["dependency"]["ownership"], "preexisting-reused")
            self.assertEqual(first["dependency"]["version"], "2.2.0")
            self.assertIn("not changed", first["dependency"]["warning"])
            installed = dest["runtime"] / "extract_url.py"
            source = (SCRIPTS / "extract_url.py").read_bytes()
            self.assertEqual(installed.read_bytes(), source)
            installed_test = dest["skill_root"] / "tests" / "test_install.py"
            self.assertTrue(installed_test.is_file())
            self.assertTrue((dest["skill_root"] / "tests" / "fixtures" / "normal.html").is_file())
            skill_text = dest["skill"].read_text(encoding="utf-8")
            self.assertIn(".cursor/skills/scraper-viewer", skill_text)
            notes = dest["skill"].parent / "notes.md"
            notes.write_text("unmanaged\n", encoding="utf-8")
            other = home / ".cursor" / "skills" / "other-skill" / "SKILL.md"
            other.parent.mkdir(parents=True)
            other.write_text("other\n", encoding="utf-8")
            mtimes = (installed.stat().st_mtime_ns, dest["skill"].stat().st_mtime_ns)
            second = install_runtime.install(home, "mac", source_for("mac"), revision_for(source_for("mac")), PYTHON, approve=True)
            self.assertEqual(second["result"], "unchanged")
            self.assertEqual(mtimes, (installed.stat().st_mtime_ns, dest["skill"].stat().st_mtime_ns))
            installed.write_text("local edit\n", encoding="utf-8")
            with self.assertRaises(InstallError):
                install_runtime.install(home, "mac", source_for("mac"), revision_for(source_for("mac")), PYTHON, approve=True)
            self.assertEqual(installed.read_text(encoding="utf-8"), "local edit\n")
            updated = install_runtime.install(home, "mac", source_for("mac"), revision_for(source_for("mac")), PYTHON, approve=True, update=True)
            self.assertEqual(updated["result"], "updated")
            self.assertEqual(installed.read_bytes(), source)
            manifest = json.loads(dest["manifest"].read_text(encoding="utf-8"))
            self.assertEqual(manifest["source_revision"], revision_for(source_for("mac")))
            self.assertFalse(manifest["venv"]["managed"])
            blocked = install_runtime.uninstall(home, "mac", confirm="")
            self.assertEqual(blocked["result"], "confirmation-required")
            self.assertTrue(installed.is_file())
            removed = install_runtime.uninstall(home, "mac", confirm="YES")
            self.assertEqual(removed["result"], "removed")
            self.assertFalse(installed.exists())
            self.assertFalse(dest["skill"].exists())
            self.assertFalse(installed_test.exists())
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
                install_runtime.install(home, "bot", source_for("bot"), revision_for(source_for("bot")), PYTHON, approve=True)
            self.assertFalse((home / "Tools").exists())

    def test_real_venv_install_is_idempotent_and_uninstall_keeps_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            first = install_runtime.install(home, "bot", source_for("bot"), revision_for(source_for("bot")), PYTHON, approve=True)
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
            second = install_runtime.install(home, "bot", source_for("bot"), revision_for(source_for("bot")), PYTHON, approve=True)
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

    def test_migration_retires_matching_old_files_and_keeps_changed_ones(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            old = home / "Tools" / "lean-input" / "runtime" / "scraper-viewer" / "extract_url.py"
            old.parent.mkdir(parents=True)
            old.write_text("managed old helper\n", encoding="utf-8")
            changed = old.parent / "local.py"
            changed.write_text("leave me\n", encoding="utf-8")
            dest = install_runtime.destinations(home, "mac")
            dest["manifest"].parent.mkdir(parents=True)
            manifest = {
                "schema_version": 1,
                "component": "scraper-viewer",
                "target": "mac",
                "files": [
                    {"path": str(old.resolve()), "sha256": hashlib.sha256(old.read_bytes()).hexdigest()},
                    {"path": str(changed.resolve()), "sha256": "0" * 64},
                ],
                "managed_directories": [str(old.parent.resolve())],
                "dependency": {"ownership": "preexisting-reused", "version": "2.2.0"},
            }
            dest["manifest"].write_text(json.dumps(manifest), encoding="utf-8")
            _fake_venv(dest["venv"])
            install_runtime.probe_python = lambda _exe: (True, "3.12.3", "test")
            install_runtime.probe_trafilatura = lambda _exe: (True, "2.2.0", "")
            install_runtime.pip_install_pinned = lambda _python: (_ for _ in ()).throw(AssertionError("pip"))
            result = install_runtime.install(home, "mac", source_for("mac"), revision_for(source_for("mac")), PYTHON, approve=True)
            self.assertEqual(result["result"], "updated")
            self.assertFalse(old.exists())
            self.assertEqual(changed.read_text(encoding="utf-8"), "leave me\n")
            self.assertTrue((dest["scripts"] / "extract_url.py").is_file())
            self.assertTrue(dest["skill"].is_file())
            self.assertTrue((dest["skill_root"] / "docs" / "Onboarding.md").is_file())
            self.assertNotIn(str(changed.resolve()), json.loads(dest["manifest"].read_text())["files"].__repr__())

    def test_legacy_component_is_reported_and_not_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            legacy_dir = home / "Tools" / "lean-input-bot" / "runtime" / "lean-input-trafilatura"
            legacy_dir.mkdir(parents=True)
            owned = legacy_dir / "extract_url.py"
            owned.write_text("original helper\n", encoding="utf-8")
            modified = legacy_dir / "actions.py"
            modified.write_text("user changed this\n", encoding="utf-8")
            output = home / "Tools" / "lean-input" / "output" / "kept.json"
            output.parent.mkdir(parents=True)
            output.write_text("{}\n", encoding="utf-8")
            manifest_path = home / "Tools" / "lean-input-bot" / "manifests" / "lean-input-trafilatura.json"
            manifest_path.parent.mkdir(parents=True)
            owned_hash = hashlib.sha256(owned.read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps({
                "schema_version": 1,
                "component": "lean-input-trafilatura",
                "target": "bot",
                "files": [
                    {"path": str(owned.resolve()), "sha256": owned_hash},
                    {"path": str(modified.resolve()), "sha256": "0" * 64},
                ],
            }), encoding="utf-8")
            dest = install_runtime.destinations(home, "bot")
            _fake_venv(dest["venv"])
            install_runtime.probe_python = lambda _exe: (True, "3.12.3", "test")
            install_runtime.probe_trafilatura = lambda _exe: (True, "2.2.0", "")
            install_runtime.pip_install_pinned = lambda _python: (_ for _ in ()).throw(AssertionError("pip"))
            source = source_for("bot")
            plan = install_runtime.install(home, "bot", source, revision_for(source), PYTHON, approve=False)
            actions = {item["action"] for item in plan["legacy"]}
            self.assertIn("legacy-owned-preserved", actions)
            self.assertIn("legacy-modified-preserved", actions)
            self.assertIn("legacy-manifest-preserved", actions)
            self.assertNotIn("retire", actions)
            result = install_runtime.install(home, "bot", source, revision_for(source), PYTHON, approve=True)
            self.assertEqual(result["result"], "installed")
            self.assertEqual(owned.read_text(encoding="utf-8"), "original helper\n")
            self.assertEqual(modified.read_text(encoding="utf-8"), "user changed this\n")
            self.assertTrue(manifest_path.is_file())
            self.assertEqual(output.read_text(encoding="utf-8"), "{}\n")
            self.assertTrue((dest["venv"] / "pyvenv.cfg").is_file())
            self.assertTrue((dest["skill_root"] / "tests" / "test_install.py").is_file())

    def test_bot_registration_note_names_the_skill_library(self):
        note = install_runtime._registration("bot")["note"]
        self.assertEqual(
            note,
            "Files under ~/Tools/lean-input-bot are not a registered Grok Bot skill "
            "until it is saved in the Grok Bot skill library as scraper-viewer; "
            "it is active once the Bot can load it by name.",
        )
        self.assertNotIn("Connect apps", note)


if __name__ == "__main__":
    unittest.main()
