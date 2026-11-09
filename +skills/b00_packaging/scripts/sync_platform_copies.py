"""Copy the canonical helper source into each delivered platform folder.

Edit shared behavior in ``+skills/b10_lean_input``. Run this script so
``bot/scripts`` and ``mac/scripts`` stay identical to that source. Platform
``run.py`` and ``SKILL.md`` files are not overwritten. ``win`` is not created.
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "+skills" / "b10_lean_input" / "scripts"))

from constants import RUNTIME_FILES  # noqa: E402

PLATFORMS = ("bot", "mac")
CANON_SCRIPTS = REPO / "+skills" / "b10_lean_input" / "scripts"
CANON_DOCS = REPO / "+docs" / "b11_Scraper-Viewer"
PATTERN = REPO / "+docs" / "b12_Lean-Input-JQ" / "Pattern-jq.md"
COMMON_TESTS = (
    "test_unit.py",
    "test_actions.py",
    "test_install.py",
    "test_scrape_options.py",
    "test_d11_index.py",
    "test_integration.py",
    "live_smoke.py",
)
CANON_TESTS = REPO / "+skills" / "b10_lean_input" / "tests"


def _copy(src: Path, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(src.read_bytes())


def sync(repo: Path = REPO):
    for platform in PLATFORMS:
        folder = repo / "+skills" / "b11_scraper-viewer" / platform
        for name in RUNTIME_FILES:
            _copy(CANON_SCRIPTS / name, folder / "scripts" / name)
        docs = folder / "docs"
        for path in sorted(CANON_DOCS.glob("*.md")):
            _copy(path, docs / path.name)
        if PATTERN.is_file():
            _copy(PATTERN, docs / "Pattern-jq.md")
        for name in COMMON_TESTS:
            _copy(CANON_TESTS / name, folder / "tests" / name)
        fixtures = CANON_TESTS / "fixtures"
        if fixtures.is_dir():
            for path in sorted(item for item in fixtures.rglob("*") if item.is_file()):
                _copy(path, folder / "tests" / "fixtures" / path.relative_to(fixtures))
    return 0


if __name__ == "__main__":
    sys.exit(sync())
