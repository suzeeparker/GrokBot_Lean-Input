"""Compare two candidate trees or zip archives by payload hash and revision.

Use this after a merge to see whether a rebuilt package matches the tested candidate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import zipfile


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def materialize(path: Path, scratch: Path) -> Path:
    if path.is_dir():
        return path
    if path.suffix != ".zip":
        raise SystemExit(f"Not a directory or zip: {path}")
    with zipfile.ZipFile(path) as handle:
        names = handle.namelist()
        if any(name.startswith("/") or ".." in Path(name).parts or ".git/" in name for name in names):
            raise SystemExit(f"Unsafe path in {path}")
        dest = scratch / path.stem
        handle.extractall(dest)
    children = [item for item in dest.iterdir()]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return dest


def load_candidate(root: Path) -> dict:
    return json.loads((root / "CANDIDATE.json").read_text(encoding="utf-8"))


def compare(left: Path, right: Path) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp)
        left_root = materialize(left, scratch / "left")
        right_root = materialize(right, scratch / "right")
        left_meta = load_candidate(left_root)
        right_meta = load_candidate(right_root)
        left_files = left_meta["files"]
        right_files = right_meta["files"]
        shared = sorted(set(left_files) & set(right_files))
        differing = [name for name in shared if left_files[name] != right_files[name]]
        runtime = [name for name in differing if name.startswith("runtime/")]
        return {
            "left_revision": left_meta["source_revision"],
            "right_revision": right_meta["source_revision"],
            "left_target": left_meta["target"],
            "right_target": right_meta["target"],
            "only_left": sorted(set(left_files) - set(right_files)),
            "only_right": sorted(set(right_files) - set(left_files)),
            "differing": differing,
            "runtime_differs": bool(runtime),
            "same_revision": left_meta["source_revision"] == right_meta["source_revision"],
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compare two candidate packages.")
    parser.add_argument("left")
    parser.add_argument("right")
    args = parser.parse_args(argv)
    report = compare(Path(args.left), Path(args.right))
    print(json.dumps(report, indent=2))
    return 1 if report["runtime_differs"] else 0


if __name__ == "__main__":
    sys.exit(main())
