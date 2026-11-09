"""Install and remove the Trafilatura runtime without touching unrelated files.

The script uses the standard library only. It never imports Trafilatura.
Passing ``--approve`` or ``--confirm YES`` is a separate step from printing a plan.
File copies do not register a Grok Bot skill.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import uuid

from constants import COMPATIBLE_MAJOR, COMPONENT, PYTHON_MIN, RUNTIME_FILES, TRAFILATURA_PIN


class InstallError(Exception):
    def __init__(self, message, code=2):
        super().__init__(message)
        self.code = code


class Journal:
    def __init__(self):
        self.created_files = []
        self.created_dirs = []
        self.created_venv = None
        self.replacements = []
        self.done = False

    def rollback(self):
        if self.done:
            return
        for path, old in reversed(self.replacements):
            path.write_bytes(old)
        for path in reversed(self.created_files):
            if path.is_file() and not path.is_symlink():
                path.unlink()
        if self.created_venv is not None and self.created_venv.exists():
            shutil.rmtree(self.created_venv)
        for directory in reversed(self.created_dirs):
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()
        self.done = True

    def commit(self):
        self.done = True


def destinations(home, target):
    home = Path(home).expanduser().resolve()
    if target == "bot":
        base = home / "Tools" / "lean-input-bot"
        skill = base / "skill-source" / COMPONENT / "SKILL.md"
    elif target == "mac":
        base = home / "Tools" / "lean-input"
        skill = home / ".cursor" / "skills" / COMPONENT / "SKILL.md"
    else:
        raise InstallError(f"Unknown target {target}")
    return {
        "home": home,
        "runtime": base / "runtime" / COMPONENT,
        "skill": skill,
        "venv": base / ".venv",
        "manifest": base / "manifests" / f"{COMPONENT}.json",
        "output": home / "Tools" / "lean-input" / "output",
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def resolve_source(root, target):
    root = Path(root).expanduser().resolve()
    repo_script = root / "+skills" / "b10_lean_input" / "scripts" / "extract_url.py"
    package_script = root / "runtime" / "extract_url.py"
    if repo_script.is_file():
        skill_name = "bot" if target == "bot" else "cursor"
        skill = root / "+skills" / "b11_lean-input-trafilatura" / skill_name / "SKILL.md"
        onboarding = root / "+docs" / "b10_Lean-Input" / "Onboarding.md"
        runtime = root / "+skills" / "b10_lean_input" / "scripts"
        layout = "repo"
        candidate = None
    elif package_script.is_file():
        skill = root / "SKILL.md"
        onboarding = root / "docs" / "Onboarding.md"
        runtime = root / "runtime"
        layout = "package"
        candidate = root / "CANDIDATE.json"
    else:
        raise InstallError(f"No lean-input payload at {root}")
    files = {name: runtime / name for name in RUNTIME_FILES}
    files["ONBOARDING.md"] = onboarding
    files["SKILL.md"] = skill
    missing = [str(path) for path in files.values() if not path.is_file()]
    if missing:
        raise InstallError("Payload is incomplete: " + ", ".join(missing))
    packaged_revision = None
    if candidate is not None and candidate.is_file():
        try:
            packaged_revision = json.loads(candidate.read_text(encoding="utf-8"))["source_revision"]
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            raise InstallError(f"CANDIDATE.json cannot be read: {exc}") from exc
    return {
        "root": root,
        "layout": layout,
        "files": files,
        "packaged_revision": packaged_revision,
    }


def resolve_revision(source, requested):
    packaged = source["packaged_revision"]
    if packaged and requested and packaged != requested:
        raise InstallError("Source revision does not match CANDIDATE.json")
    if packaged and not requested:
        return packaged
    if not requested:
        raise InstallError("A source revision is required")
    return requested


def load_manifest(path: Path):
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InstallError(f"Existing manifest cannot be read: {exc}") from exc
    if data.get("schema_version") != 1 or data.get("component") != COMPONENT:
        raise InstallError("Existing manifest is not a lean-input-trafilatura schema 1 manifest")
    return data


def manifest_index(manifest):
    if not manifest:
        return {}
    return {entry["path"]: entry["sha256"] for entry in manifest.get("files", [])}


def desired_pairs(source, dest):
    pairs = []
    for name in RUNTIME_FILES:
        pairs.append((source["files"][name], dest["runtime"] / name))
    pairs.append((source["files"]["ONBOARDING.md"], dest["runtime"] / "ONBOARDING.md"))
    pairs.append((source["files"]["SKILL.md"], dest["skill"]))
    return pairs


def classify_file(dest: Path, source: Path, owned: dict, update: bool):
    data = source.read_bytes()
    desired = sha256_bytes(data)
    key = str(dest)
    if dest.is_symlink():
        return {"path": key, "action": "block", "reason": f"{key} is a symlink and will not be replaced"}
    if dest.exists() and dest.is_dir():
        return {"path": key, "action": "block", "reason": f"{key} is a directory"}
    if not dest.exists():
        return {"path": key, "action": "create", "sha256": desired, "bytes": data}
    current = sha256_file(dest)
    if key not in owned:
        return {
            "path": key,
            "action": "block",
            "reason": f"{key} already exists and is not owned by the lean-input manifest",
        }
    if current == desired:
        return {"path": key, "action": "keep", "sha256": desired, "bytes": data}
    if update:
        return {"path": key, "action": "replace", "sha256": desired, "bytes": data}
    return {
        "path": key,
        "action": "block",
        "reason": f"{key} is managed and differs from this candidate. Pass --update to replace it. It was not changed.",
    }


def probe_python(executable):
    path = Path(executable)
    if not path.is_absolute():
        return False, "", "Interpreter must be an absolute path"
    if not os.access(path, os.X_OK):
        return False, "", f"Interpreter is not executable: {executable}"
    if not hasattr(signal, "SIGALRM"):
        return False, "", "Unix SIGALRM is required (Linux or macOS)"
    script = (
        "import sys,ssl,venv\n"
        "print('%d.%d.%d' % sys.version_info[:3])\n"
        "print(ssl.OPENSSL_VERSION)\n"
    )
    try:
        proc = subprocess.run([str(path), "-c", script], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, "", str(exc)
    if proc.returncode != 0:
        detail = proc.stderr.strip() or "Python cannot import ssl and venv"
        return False, "", detail
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if not lines:
        return False, "", "Interpreter did not report a version"
    version = lines[0]
    try:
        parts = tuple(int(piece) for piece in version.split("."))
    except ValueError:
        return False, version, f"Unreadable Python version {version}"
    if parts < PYTHON_MIN:
        return False, version, f"Python {version} is below 3.10"
    detail = lines[1] if len(lines) > 1 else ""
    return True, version, detail


def probe_trafilatura(venv_python):
    script = "import trafilatura\nprint(trafilatura.__version__)\n"
    try:
        proc = subprocess.run([str(venv_python), "-c", script], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, None, str(exc)
    if proc.returncode != 0:
        return False, None, proc.stderr.strip() or "trafilatura is not installed"
    version = proc.stdout.strip().splitlines()[-1].strip()
    return True, version, ""


def create_venv(base_python, venv_path: Path):
    venv_path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [str(base_python), "-m", "venv", str(venv_path)],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if proc.returncode != 0:
        raise InstallError(proc.stderr.strip() or "venv creation failed")


def pip_install_pinned(venv_python):
    proc = subprocess.run(
        [
            str(venv_python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
            f"trafilatura=={TRAFILATURA_PIN}",
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proc.returncode != 0:
        raise InstallError(proc.stderr.strip() or proc.stdout.strip() or "pip install failed")
    ok, version, err = probe_trafilatura(venv_python)
    if not ok or version != TRAFILATURA_PIN:
        raise InstallError(f"Installed Trafilatura did not match pin {TRAFILATURA_PIN}: {version or err}")
    return version


def _major(version):
    try:
        return int(str(version).split(".", 1)[0])
    except ValueError as exc:
        raise InstallError(f"Unreadable Trafilatura version {version}") from exc


def inspect_venv(venv_path: Path, base_python):
    python = venv_path / "bin" / "python"
    if not venv_path.exists():
        return {"action": "create", "python": python}
    if not (venv_path / "pyvenv.cfg").is_file() or not python.is_file():
        raise InstallError(f"{venv_path} exists and is not a usable virtual environment. It was left unchanged.")
    ok, version, detail = probe_python(python)
    if not ok:
        raise InstallError(f"Existing virtual environment is not usable: {detail}")
    return {"action": "reuse", "python": python, "version": version, "detail": detail}


def dependency_plan(venv_python, venv_exists):
    if not venv_exists:
        return {
            "action": "install",
            "version": None,
            "ownership": "installed-by-lean-input",
            "warning": None,
        }
    ok, version, _err = probe_trafilatura(venv_python)
    if not ok:
        return {
            "action": "install",
            "version": None,
            "ownership": "installed-by-lean-input",
            "warning": None,
        }
    if _major(version) != COMPATIBLE_MAJOR:
        raise InstallError(
            f"Trafilatura {version} is already installed and is outside the 2.x range this slice accepts. "
            "It was not upgraded, downgraded, or replaced."
        )
    warning = None
    if version != TRAFILATURA_PIN:
        warning = (
            f"Reused preexisting Trafilatura {version}. "
            f"The integration tests for this candidate ran against {TRAFILATURA_PIN}. "
            "The installed version was not changed."
        )
    return {
        "action": "reuse",
        "version": version,
        "ownership": "preexisting-reused",
        "warning": warning,
    }


def _ensure_parent(path: Path, journal: Journal):
    missing = []
    current = path.parent
    while not current.exists():
        missing.append(current)
        current = current.parent
    path.parent.mkdir(parents=True, exist_ok=True)
    for directory in reversed(missing):
        journal.created_dirs.append(directory)


def _create_file(path: Path, data: bytes, journal: Journal):
    _ensure_parent(path, journal)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
    journal.created_files.append(path)


def _replace_file(path: Path, data: bytes, journal: Journal):
    old = path.read_bytes()
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(temporary, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(temporary, path)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise
    journal.replacements.append((path, old))


def _registration(target):
    if target == "bot":
        return {
            "state": "pending-host-api",
            "note": (
                "Files under ~/Tools/lean-input-bot are not a registered Grok Bot skill "
                "until it is saved in the Grok Bot skill library as lean-input-trafilatura; "
                "it is active once the Bot can load it by name."
            ),
        }
    return {
        "state": "cursor-skill-file",
        "note": (
            "SKILL.md was placed at ~/.cursor/skills/lean-input-trafilatura/ for Cursor discovery. "
            "Confirm it is listed in Customize, Skills, before treating it as active. "
            "Do not turn on Sync Skills for Cloud Agents as part of this install."
        ),
    }


def _build_manifest(target, revision, layout, base_python, venv_python, venv_ownership, dependency, file_records, dest):
    managed_directories = sorted(
        {
            str(dest["runtime"]),
            str(dest["skill"].parent),
            str(dest["manifest"].parent),
        }
    )
    return {
        "schema_version": 1,
        "component": COMPONENT,
        "target": target,
        "source_revision": revision,
        "source_layout": layout,
        "python_min": "3.10",
        "trafilatura_pin": TRAFILATURA_PIN,
        "base_interpreter": str(base_python),
        "interpreter": str(venv_python),
        "venv": {
            "path": str(dest["venv"]),
            "ownership": venv_ownership,
            "managed": False,
        },
        "dependency": {
            "name": "trafilatura",
            "version": dependency["version"],
            "pin": TRAFILATURA_PIN,
            "ownership": dependency["ownership"],
            "compatible_major": COMPATIBLE_MAJOR,
            "warning": dependency["warning"],
        },
        "registration": _registration(target),
        "files": file_records,
        "managed_directories": managed_directories,
    }


def _preserve_ownership(existing, created_now, field):
    if created_now:
        return "created-by-lean-input" if field == "venv" else "installed-by-lean-input"
    if existing and existing.get(field, {}).get("ownership"):
        return existing[field]["ownership"]
    return "preexisting-reused"


def install(home, target, source_root, source_revision, python, approve=False, update=False):
    dest = destinations(home, target)
    source = resolve_source(source_root, target)
    revision = resolve_revision(source, source_revision)
    ok, _version, detail = probe_python(python)
    if not ok:
        raise InstallError(detail)
    existing = load_manifest(dest["manifest"])
    if existing and existing.get("target") not in (None, target):
        raise InstallError("Manifest target does not match this install target")
    owned = manifest_index(existing)
    classified = [classify_file(path, src, owned, update) for src, path in desired_pairs(source, dest)]
    blocked = [item for item in classified if item["action"] == "block"]
    if blocked:
        raise InstallError(blocked[0]["reason"])
    venv_info = inspect_venv(dest["venv"], python)
    dep = dependency_plan(venv_info["python"], venv_info["action"] == "reuse")
    if dep["action"] == "reuse" and existing and existing.get("dependency", {}).get("ownership") == "installed-by-lean-input":
        dep["ownership"] = "installed-by-lean-input"
    file_records = [{"path": item["path"], "sha256": item["sha256"]} for item in classified]
    file_records.sort(key=lambda item: item["path"])
    venv_ownership = _preserve_ownership(existing, venv_info["action"] == "create", "venv")
    prospective = _build_manifest(
        target,
        revision,
        source["layout"],
        python,
        venv_info["python"],
        venv_ownership,
        dep,
        file_records,
        dest,
    )
    file_changes = [item for item in classified if item["action"] != "keep"]
    unchanged = not file_changes and venv_info["action"] == "reuse" and existing == prospective
    plan = {
        "result": "unchanged" if unchanged else "plan",
        "target": target,
        "source_revision": revision,
        "source_layout": source["layout"],
        "approval": "granted" if approve else "required",
        "files": [{"path": item["path"], "action": item["action"]} for item in classified],
        "venv": {"path": str(dest["venv"]), "action": venv_info["action"], "ownership": venv_ownership},
        "dependency": dep,
        "registration": prospective["registration"],
        "preserved": ["shared virtual environment on uninstall", "output files", "unmanaged files", "other skills"],
    }
    if not approve:
        return plan
    if unchanged:
        plan["result"] = "unchanged"
        return plan
    journal = Journal()
    try:
        if venv_info["action"] == "create":
            _ensure_parent(dest["venv"], journal)
            create_venv(python, dest["venv"])
            journal.created_venv = dest["venv"]
            dep = dependency_plan(venv_info["python"], True)
        else:
            dep = dependency_plan(venv_info["python"], True)
        if dep["action"] == "reuse" and existing and existing.get("dependency", {}).get("ownership") == "installed-by-lean-input":
            if existing.get("dependency", {}).get("version") == dep["version"]:
                dep["ownership"] = "installed-by-lean-input"
        for item in classified:
            path = Path(item["path"])
            if item["action"] == "create":
                _create_file(path, item["bytes"], journal)
            elif item["action"] == "replace":
                _replace_file(path, item["bytes"], journal)
        if dep["action"] == "install":
            version = pip_install_pinned(venv_info["python"])
            dep = {
                "action": "install",
                "version": version,
                "ownership": "installed-by-lean-input",
                "warning": None,
            }
        file_records = [{"path": item["path"], "sha256": item["sha256"]} for item in classified]
        file_records.sort(key=lambda item: item["path"])
        manifest = _build_manifest(
            target,
            revision,
            source["layout"],
            python,
            venv_info["python"],
            "created-by-lean-input" if journal.created_venv is not None else venv_ownership,
            dep,
            file_records,
            dest,
        )
        encoded = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        if dest["manifest"].exists():
            _replace_file(dest["manifest"], encoded, journal)
        else:
            _create_file(dest["manifest"], encoded, journal)
        journal.commit()
    except BaseException:
        journal.rollback()
        raise
    result_name = "updated" if any(item["action"] == "replace" for item in classified) else "installed"
    return {
        "result": result_name,
        "target": target,
        "source_revision": revision,
        "interpreter": str(venv_info["python"]),
        "dependency": dep,
        "registration": manifest["registration"],
        "files": [item["path"] for item in file_records],
    }


def uninstall(home, target, confirm=""):
    dest = destinations(home, target)
    manifest = load_manifest(dest["manifest"])
    preserved = {
        "venv": str(dest["venv"]),
        "output": str(dest["output"]),
        "dependencies": "Trafilatura and the shared virtual environment are not removed",
        "unmanaged_files": "Files that are absent from the manifest, or whose checksum changed, are kept",
    }
    if manifest is None:
        return {"result": "nothing-managed", "removed": [], "skipped": [], "preserved": preserved}
    plan = []
    for entry in manifest.get("files", []):
        path = Path(entry["path"])
        if path.is_symlink():
            plan.append({"path": entry["path"], "action": "skip-symlink"})
        elif not path.exists():
            plan.append({"path": entry["path"], "action": "already-absent"})
        elif sha256_file(path) != entry["sha256"]:
            plan.append({"path": entry["path"], "action": "skip-changed"})
        else:
            plan.append({"path": entry["path"], "action": "remove"})
    if confirm != "YES":
        return {
            "result": "confirmation-required",
            "plan": plan,
            "preserved": preserved,
            "message": "No files were removed. Re-run with confirmation YES only after the owner agrees to this list.",
        }
    removed = []
    skipped = []
    for item in plan:
        path = Path(item["path"])
        if item["action"] == "remove":
            path.unlink()
            removed.append(item["path"])
        elif item["action"] == "already-absent":
            removed.append(item["path"])
        else:
            skipped.append(item)
    for directory in sorted(manifest.get("managed_directories", []), key=len, reverse=True):
        candidate = Path(directory)
        if candidate.is_dir() and not any(candidate.iterdir()):
            candidate.rmdir()
    if skipped:
        manifest["files"] = [entry for entry in manifest["files"] if entry["path"] in {item["path"] for item in skipped}]
        dest["manifest"].parent.mkdir(parents=True, exist_ok=True)
        encoded = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        dest["manifest"].write_bytes(encoded)
        return {"result": "partial", "removed": removed, "skipped": skipped, "preserved": preserved}
    if dest["manifest"].is_file():
        dest["manifest"].unlink()
    manifest_parent = dest["manifest"].parent
    if manifest_parent.is_dir() and not any(manifest_parent.iterdir()):
        manifest_parent.rmdir()
    return {"result": "removed", "removed": removed, "skipped": [], "preserved": preserved}


def explain(home, target):
    dest = destinations(home, target)
    manifest = None
    manifest_path = dest["manifest"]
    if manifest_path.is_file():
        manifest = load_manifest(manifest_path)
    location = "Grok Bot computer" if target == "bot" else "Cursor on this Mac"
    interpreter = str(dest["venv"] / "bin" / "python")
    version = None
    warning = None
    if manifest:
        version = manifest.get("dependency", {}).get("version")
        warning = manifest.get("dependency", {}).get("warning")
        interpreter = manifest.get("interpreter", interpreter)
    lines = [
        "lean-input-trafilatura extracts the main text and available metadata of one public HTTP or HTTPS page",
        "into a UTF-8 JSON file and a separate character-count sidecar. It is the first Lean Input tool.",
        "jq and the other Lean Input tools are not part of this skill.",
        f"Execution location: {location}.",
        "Required input: one public http or https URL. An output path is optional.",
        "Examples:",
        "  lean-input-trafilatura install",
        "  lean-input-trafilatura uninstall",
        "  lean-input-trafilatura explain",
        "  lean-input-trafilatura do https://example.com/",
        "  lean-input-trafilatura scrape https://example.com/",
        "  lean-input-trafilatura https://example.com/",
        "scrape is an alias of do and follows the same rules.",
        "scrape and do with only a URL are the page option.",
        "scrape seo, scrape aeo, and scrape schema can be combined. scrape all runs all four.",
        "An unknown option word before the URL is refused and nothing is fetched.",
        "A hostname with no scheme, such as sicomm.net or www.sicomm.net/path, is requested as https:// plus that token.",
        "The summary says https:// was added. http:// is never added. localhost and a nonpublic IP are refused.",
        "A missing seo, aeo, or schema element is the string not found. The command prints one summary.",
        f"Interpreter: {interpreter}",
        f"Helpers: {dest['runtime']}",
        f"Skill file: {dest['skill']}",
        f"Default output directory: {dest['output']}",
        f"Pinned fresh install: trafilatura=={TRAFILATURA_PIN}",
        f"Known installed Trafilatura: {version if version else 'not recorded'}",
    ]
    if warning:
        lines.append(warning)
    if manifest:
        lines.append(f"Source revision: {manifest.get('source_revision')}")
        lines.append(manifest.get("registration", {}).get("note", ""))
    else:
        lines.append("This target has no lean-input-trafilatura manifest. Nothing was installed by this command.")
    lines.extend(
        [
            "Limitations: heuristic extraction can drop or flatten tables, links, and browser-rendered content.",
            "JavaScript challenges, logins, and paywalls are not bypassed.",
            "Counts are Unicode code points in the decoded HTML, the extracted text, and the serialized JSON file.",
            "They are not bytes, tokens, or estimated savings.",
            "This command did not change files.",
        ]
    )
    return {
        "result": "explain",
        "installed": manifest is not None,
        "target": target,
        "text": "\n".join(lines) + "\n",
    }


def _print(payload):
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Install or remove lean-input-trafilatura files.")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_target(command):
        command.add_argument("--target", choices=("bot", "mac"), required=True)
        command.add_argument("--home", required=True)

    install_cmd = sub.add_parser("install")
    add_target(install_cmd)
    install_cmd.add_argument("--source-root", required=True)
    install_cmd.add_argument("--source-revision")
    install_cmd.add_argument("--python", required=True)
    install_cmd.add_argument("--approve", action="store_true")
    install_cmd.add_argument("--update", action="store_true")

    remove_cmd = sub.add_parser("uninstall")
    add_target(remove_cmd)
    remove_cmd.add_argument("--confirm", default="")

    explain_cmd = sub.add_parser("explain")
    add_target(explain_cmd)

    args = parser.parse_args(argv)
    try:
        if args.command == "install":
            payload = install(
                args.home,
                args.target,
                args.source_root,
                args.source_revision,
                args.python,
                approve=args.approve,
                update=args.update,
            )
            _print(payload)
            return 3 if payload.get("approval") == "required" else 0
        if args.command == "uninstall":
            payload = uninstall(args.home, args.target, args.confirm)
            _print(payload)
            if payload["result"] == "confirmation-required":
                return 3
            if payload["result"] == "partial":
                return 4
            return 0
        payload = explain(args.home, args.target)
        sys.stdout.write(payload["text"])
        return 0
    except InstallError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.exit(main())
