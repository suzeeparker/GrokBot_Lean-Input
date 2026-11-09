"""Interpret one lean-input-trafilatura request.

The action is the first standalone word: install, uninstall, explain, or do.
scrape is an alias of do. Any other first word leaves the whole task on the implied do action.
This file is the helper the skill runs. It is not a product shell command
and it does not define a slash command.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import install_runtime
from install_runtime import InstallError

ACTIONS = {"install", "uninstall", "explain", "do"}
DO_ALIASES = {"do", "scrape"}
URL_RE = re.compile(r"https?://[^\s<>'\"]+")
OUTPUT_RE = re.compile(r"(?:^|\s)(?:--output|output)\s+(?:\"([^\"]+)\"|(\S+))", re.IGNORECASE)
RETAIN_RE = re.compile(r"(?:--retain-html|\bretain\s+html\b)", re.IGNORECASE)


def parse_dispatch(text):
    """Return ``(action, task)`` from the user's text."""
    if not isinstance(text, str):
        return "do", ""
    current = text.strip()
    if current.startswith("#"):
        current = current[1:].strip()
    if not current:
        return "do", ""
    token, _, rest = current.partition(" ")
    if token.casefold() == "lean-input-trafilatura":
        current = rest.strip()
        if not current:
            return "do", ""
        token, _, rest = current.partition(" ")
    folded = token.casefold()
    if token.isalpha() and (folded in ACTIONS or folded in DO_ALIASES):
        if folded in DO_ALIASES:
            return "do", rest.strip()
        return folded, rest.strip()
    return "do", current


def parse_task(task):
    """Return ``(urls, output, retain)`` from a do task."""
    if not task:
        return [], None, False
    retain = RETAIN_RE.search(task) is not None
    search_in = task
    output = None
    match = OUTPUT_RE.search(task)
    if match:
        output = (match.group(1) or match.group(2)).rstrip(".,);")
        search_in = task[: match.start()] + " " + task[match.end() :]
    urls = [raw.rstrip(".,);]") for raw in URL_RE.findall(search_in)]
    return urls, output, retain


def _offer(home, target):
    dest = install_runtime.destinations(home, target)
    interpreter = dest["venv"] / "bin" / "python"
    helper = dest["runtime"] / "extract_url.py"
    return (
        "The lean-input-trafilatura runtime is not installed. Nothing was installed.\n"
        "Ask the owner to approve install before changing this computer.\n"
        f"Expected interpreter: {interpreter}\n"
        f"Expected helper: {helper}\n"
        "After approval, run the installer from the unpacked candidate or the repository "
        "with --approve. Do not install silently.\n"
    )


def perform_do(task, home, target):
    urls, output, retain = parse_task(task)
    dest = install_runtime.destinations(home, target)
    helper = dest["runtime"] / "extract_url.py"
    python = dest["venv"] / "bin" / "python"
    if not helper.is_file() or not os.access(python, os.X_OK):
        sys.stdout.write(_offer(home, target))
        return 10
    if not urls:
        sys.stdout.write("A public HTTP or HTTPS URL is required. Nothing was fetched.\n")
        return 2
    if len(urls) > 1:
        sys.stdout.write("More than one URL was present. Only the first URL is extracted.\n")
    command = [str(python), str(helper), urls[0], "--target", target]
    if output:
        command.extend(["--output", output])
    if retain:
        command.append("--retain-html")
    completed = subprocess.run(command, check=False)
    return completed.returncode


def dispatch(message, home, target, source_root=None, source_revision=None, python=None, approve=False, confirm="", update=False):
    action, task = parse_dispatch(message)
    if action == "explain":
        payload = install_runtime.explain(home, target)
        sys.stdout.write(payload["text"])
        return 0
    if action == "install":
        if not source_root or not python:
            sys.stdout.write("Install needs an absolute --python and a --source-root. Nothing was changed.\n")
            return 2
        payload = install_runtime.install(
            home,
            target,
            source_root,
            source_revision,
            python,
            approve=approve,
            update=update,
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 3 if payload.get("approval") == "required" else 0
    if action == "uninstall":
        payload = install_runtime.uninstall(home, target, confirm)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        if payload["result"] == "confirmation-required":
            return 3
        if payload["result"] == "partial":
            return 4
        return 0
    return perform_do(task, home, target)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Dispatch one lean-input-trafilatura request.")
    parser.add_argument("--message", required=True)
    parser.add_argument("--target", choices=("bot", "mac"), required=True)
    parser.add_argument("--home", required=True)
    parser.add_argument("--source-root")
    parser.add_argument("--source-revision")
    parser.add_argument("--python")
    parser.add_argument("--approve", action="store_true")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--update", action="store_true")
    args = parser.parse_args(argv)
    try:
        return dispatch(
            args.message,
            args.home,
            args.target,
            source_root=args.source_root,
            source_revision=args.source_revision,
            python=args.python,
            approve=args.approve,
            confirm=args.confirm,
            update=args.update,
        )
    except InstallError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.exit(main())
