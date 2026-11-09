"""Run each shipped archive's own tests from the unpacked zip.

Linux results are not Mac or Grok Bot app acceptance.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "+skills" / "b00_packaging" / "scripts"))

import build_candidates  # noqa: E402

PYTHON = Path("/tmp/lean-tf-venv/bin/python")
REVISION = "d" * 40
EXPECTED_SKIPS = {"bot": 4, "mac": 4}


class ShippedArchiveTests(unittest.TestCase):
    def test_unpacked_archives_exercise_their_own_install_tests(self):
        self.assertTrue(PYTHON.is_file(), "isolated Trafilatura interpreter is required")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            built = build_candidates.build(ROOT, REVISION, out)
            for target, archive in built["archives"].items():
                with self.subTest(target=target):
                    unpacked = Path(tmp) / f"unpacked-{target}"
                    with zipfile.ZipFile(archive) as handle:
                        handle.extractall(unpacked)
                    package = next(unpacked.rglob("CANDIDATE.json")).parent
                    self.assertTrue((package / "tests" / "fixtures" / "normal.html").is_file())
                    self.assertTrue((package / "tests" / "test_install.py").is_file())
                    completed = subprocess.run(
                        [str(PYTHON), "-m", "unittest", "discover", "-s", "tests"],
                        cwd=package,
                        capture_output=True,
                        text=True,
                        timeout=180,
                    )
                    output = completed.stdout + completed.stderr
                    self.assertEqual(completed.returncode, 0, output[-4000:])
                    self.assertIn(f"OK (skipped={EXPECTED_SKIPS[target]})", output)
                    self.assertNotIn("skipped=7", output)


if __name__ == "__main__":
    unittest.main()
