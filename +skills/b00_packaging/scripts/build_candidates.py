"""Build independent bot and Mac candidate archives from one canonical tree.

The archives contain no ``.git`` directory. They are candidates, not a release.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "+skills" / "b10_lean_input" / "scripts"))

from constants import RUNTIME_FILES, TRAFILATURA_PIN  # noqa: E402

DOCS = (
    "README.md",
    "Setup.md",
    "Actions.md",
    "Development.md",
    "Update.md",
    "Uninstall.md",
    "Lifecycle.md",
    "Onboarding.md",
    "Review-v1.11.md",
    "Acceptance.md",
    "Candidate-test-evidence.md",
    "Vertical-slice.md",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy(src: Path, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(src.read_bytes())


def build_tree(repo: Path, target: str, revision: str, out_dir: Path) -> Path:
    short = revision[:12]
    root = out_dir / f"scraper-viewer-{target}-candidate-{short}"
    if root.exists():
        raise SystemExit(f"Refusing to replace {root}")
    skill_group = "bot" if target == "bot" else "cursor"
    skill = repo / "+skills" / "b11_scraper-viewer" / skill_group / "SKILL.md"
    _copy(skill, root / "SKILL.md")
    shared = repo / "+skills" / "b10_lean_input" / "scripts"
    for name in RUNTIME_FILES:
        _copy(shared / name, root / "runtime" / name)
    docs = repo / "+docs" / "B11_Scraper-Viewer"
    for name in DOCS:
        _copy(docs / name, root / "docs" / name)
    _copy(repo / "+docs" / "b12_Lean-Input-JQ" / "Pattern-jq.md", root / "docs" / "Pattern-jq.md")
    readme = (
        f"# scraper-viewer {target} candidate\n\n"
        "This archive is an unmerged candidate snapshot. It is not a stable release and it has no git tag.\n"
        "It is not a git checkout. Do not clone the repository onto the bot computer or the Mac.\n"
        f"Source revision: `{revision}`\n\n"
        "GitHub `master` is authoritative after merge. Until the parent confirms Grok Bot app acceptance "
        "and Mac Cursor acceptance, do not merge.\n\n"
        "Install from this unpacked directory with the absolute base interpreter. Run the plan first, "
        "then repeat with `--approve` only after the owner agrees.\n\n"
        "```sh\n"
        'BASE_PYTHON="/absolute/path/to/python3"\n'
        'UNPACKED="/absolute/path/to/this/directory"\n'
        '"$BASE_PYTHON" "$UNPACKED/runtime/install_runtime.py" install \\\n'
        f'  --target {target} \\\n'
        '  --home "$HOME" \\\n'
        '  --source-root "$UNPACKED" \\\n'
        '  --python "$BASE_PYTHON"\n'
        "```\n\n"
        "Registration and tests are in `docs/Onboarding.md` and `docs/Setup.md`.\n"
    )
    (root / "README.md").write_text(readme, encoding="utf-8")
    files = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if ".git" in Path(relative).parts:
            raise SystemExit("Refusing to pack .git")
        files[relative] = sha256_file(path)
    candidate = {
        "name": "scraper-viewer",
        "channel": "candidate",
        "target": target,
        "source_revision": revision,
        "source_revision_short": short,
        "stable_release": False,
        "git_tag": None,
        "trafilatura_pin": TRAFILATURA_PIN,
        "python_requires": ">=3.10",
        "not_a_git_checkout": True,
        "files": files,
    }
    # CANDIDATE.json is not listed inside itself. Its rewrite would change its own digest.
    (root / "CANDIDATE.json").write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
    return root


def zip_tree(root: Path) -> Path:
    archive = root.with_suffix(".zip")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            relative = path.relative_to(root).as_posix()
            if ".git" in Path(relative).parts or path.is_symlink():
                raise SystemExit(f"Refusing to pack {relative}")
            handle.write(path, arcname=f"{root.name}/{relative}")
    return archive


def runtime_hashes(root: Path) -> dict:
    hashes = {}
    for path in sorted((root / "runtime").iterdir()):
        if path.is_file():
            hashes[path.name] = sha256_file(path)
    return hashes


def build(repo: Path, revision: str, out_dir: Path):
    if len(revision) < 12 or any(char not in "0123456789abcdef" for char in revision.lower()):
        raise SystemExit("Revision must be a git commit id")
    out_dir.mkdir(parents=True, exist_ok=True)
    trees = {target: build_tree(repo, target, revision, out_dir) for target in ("bot", "mac")}
    bot_hashes = runtime_hashes(trees["bot"])
    mac_hashes = runtime_hashes(trees["mac"])
    if bot_hashes != mac_hashes:
        raise SystemExit("Bot and Mac runtime helpers differ")
    archives = {target: zip_tree(trees[target]) for target in trees}
    checksums = out_dir / f"scraper-viewer-candidate-{revision[:12]}.checksums.txt"
    lines = [f"source_revision {revision}", f"trafilatura_pin {TRAFILATURA_PIN}", "runtime_helpers_identical true"]
    for name in sorted(bot_hashes):
        lines.append(f"runtime/{name} {bot_hashes[name]}")
    for target, archive in archives.items():
        lines.append(f"{archive.name} {sha256_file(archive)}")
    checksums.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"trees": trees, "archives": archives, "checksums": checksums, "runtime_hashes": bot_hashes}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build bot and Mac candidate archives.")
    parser.add_argument("--revision", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--repo", default=str(REPO))
    args = parser.parse_args(argv)
    result = build(Path(args.repo), args.revision, Path(args.out))
    print(result["checksums"])
    for archive in result["archives"].values():
        print(archive)
    return 0


if __name__ == "__main__":
    sys.exit(main())
