# Development

Work happens in a coding-agent checkout on a branch. Do not clone the repository onto the Grok Bot computer or the Mac. GitHub `master` is the authoritative source after merge. Installed snapshots are not checkouts.

This slice is Trafilatura only. `+docs/b12_Lean-Input-JQ/Pattern-jq.md` records the shape for a later `lean-input-jq` skill. Do not add the other tools here.

## Isolated test environment

The tests use the standard library plus Trafilatura in a virtual environment that is not committed.

```sh
python3 -m venv /tmp/lean-input-dev-venv
/tmp/lean-input-dev-venv/bin/python -m pip install --disable-pip-version-check -r +skills/b10_lean_input/scripts/requirements.txt
/tmp/lean-input-dev-venv/bin/python -m unittest discover -s +skills/b00_packaging/tests -v
/tmp/lean-input-dev-venv/bin/python -m unittest discover -s +skills/b10_lean_input/tests -v
/tmp/lean-input-dev-venv/bin/python -m unittest discover -s +skills/b11_scraper-viewer/bot/tests -v
/tmp/lean-input-dev-venv/bin/python -m unittest discover -s +skills/b11_scraper-viewer/mac/tests -v
```

`+` and hyphens are not Python packages. Each `discover` uses the test directory itself as the import root. `+skills/b11_scraper-viewer/bot/tests/test_integration.py` imports Trafilatura and fails if the pin is not 2.3.1. `+skills/b10_lean_input/tests/test_install.py` includes one real virtual-environment install under a temporary home. Installer refusal, rollback, and uninstall tests also use a temporary home and do not point at the operator's real home.

Optional live smoke:

```sh
/tmp/lean-input-dev-venv/bin/python +skills/b11_scraper-viewer/bot/tests/live_smoke.py https://example.com/
```

A live result is evidence about that URL on that network. It is not Mac acceptance and it is not Grok Bot app acceptance.

## Packages

`+skills/b00_packaging/scripts/build_candidates.py` copies the canonical helpers into two archives and checks that those helper bytes match. Skill text differs by environment. The archives omit `.git`. They are candidates: `stable_release` is false and no git tag is created.

```sh
python3 +skills/b00_packaging/scripts/build_candidates.py --revision "$(git rev-parse HEAD)" --out /tmp/lean-candidates
python3 +skills/b00_packaging/scripts/compare_candidates.py /tmp/lean-candidates/scraper-viewer-bot-candidate-<rev>.zip /tmp/lean-candidates/scraper-viewer-mac-candidate-<rev>.zip
```

The compare exits 1 when runtime helper hashes differ. Skill text and `CANDIDATE.json` are expected to differ between bot and Mac.

## Commit subjects

Follow `CONTRIBUTING.md`. Subjects use Robin's date in `America/New_York` and a two-digit sequence for that local day. Inspect `git log` on the remote history before choosing the number. Do not amend, rebase, or force-push a published commit to rename it.

## What not to commit

Do not commit virtual environments, extraction output, install manifests from a home directory, secrets, machine ids, or candidate zip files. Those archives are build artifacts. `.gitignore` ignores virtual environments and Python caches.

## Merge

Do not merge while Grok Bot app acceptance or Mac Cursor acceptance is still open. The parent has to confirm both. After that confirmation, the coding agent may merge; a separate manual merge by the owner is not required. See `lifecycle.md`.
