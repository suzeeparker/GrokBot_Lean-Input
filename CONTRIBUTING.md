# Contributing

## Commit subjects

Use Robin's date in the `America/New_York` time zone. The date tag is five digits: the last digit of the year, the two-digit month, and the two-digit day. 8 November 2026 is `61108`. 29 May 2026 is `60529`.

The subject starts with `.(` and has no closing parenthesis. The sequence is the nth commit already using that date tag in this repository, including commits that are only on the remote, plus one. It is two digits.

```text
.(61108.05_Add Trafilatura skills
```

That subject is the whole first line: `.(`, the date tag, `.`, the sequence, `_`, then the comment. Do not add `)`.

Before choosing the sequence, read `git log` for the date tag on the local branch and on `origin`. Do not reuse a number. The next subject after `.(61108.04_...` on 8 November 2026 is `.(61108.05_...`. A later commit the same local day uses `06`, then `07`.

A commit body after a blank line is optional. The existing history uses the subject line alone. Keep the subject itself in this form either way.

Do not amend, rebase, or force-push a commit that has been pushed in order to rename it. Published history stays as it is. A destructive history rewrite needs an explicit approval from the parent first. Do not do one because a subject looks inconsistent.

## Repository layout

This is the repository standard.

- Skills and their code live under `+skills/`. Folder names are lowercase and start with a `b##_` prefix.
- Docs live under `+docs/`. The `b##` prefix is always lowercase, including under `+docs`. The name after that prefix stays capitalized, for example `b11_Scraper-Viewer`. Doc file names are capitalized, for example `Acceptance.md`.
- `b00` is packaging. `b10` is the shared Lean Input code (formerly a10). Tool numbers are `b11` scraper-viewer (the Trafilatura library), `b12` jq, `b13` ripgrep, `b14` duckdb, `b15` docling, `b16` changedetection.io, `b17` rtk, `b18` tenacity, and `b19` pydantic.
- A delivered tool has one folder per platform: `bot/`, `mac/`, and later `win/`. Each of those has `SKILL.md`, `scripts/`, `tests/`, and `docs/`. `win` is planned and is not implemented. Do not add a `win` folder until Windows support is real.
- Do not add empty placeholder folders for tools that are not implemented yet.
- Folders whose names contain `+` or `-` are not Python packages. Run scripts by path. Imports add the script directory to `sys.path` from the file's own location.
- Installed skill names do not use the `b##` prefix. `scraper-viewer` stays that name after install. `lean-input-trafilatura` is a deprecated invocation alias for one release. The macOS skill folder is `~/.cursor/skills/<skill>/` and contains `scripts/` and `docs/`. Cursor discovers that path; other macOS agents can use the same folder. The venv stays `~/Tools/lean-input/.venv/` and is not copied into the skill. Mac JSON output goes to `/Users/Shared/Repos/GrokBot_/+data/DBMSs/JSONs/d11_scraper-viewer/`, outside the lean-input repo. The bot skill folder is `~/Tools/lean-input-bot/<skill>/`. Bot JSON output stays `~/Tools/lean-input/output/`.

Planned folder names, created only when that tool has files:

| Number | `+skills/` folder | `+docs/` folder |
|---|---|---|
| b00 | `b00_packaging` | |
| b10 | `b10_lean_input` | `b10_Lean-Input` |
| b11 | `b11_scraper-viewer` | `b11_Scraper-Viewer` |
| b12 | `b12_lean-input-jq` | `b12_Lean-Input-JQ` |
| b13 | `b13_lean-input-ripgrep` | `b13_Lean-Input-RipGrep` |
| b14 | `b14_lean-input-duck-db` | `b14_Lean-Input-DuckDB` |
| b15 | `b15_lean-input-docling` | `b15_Lean-Input-Docling` |
| b16 | `b16_change-detection-io` | `b16_ChangeDetection.io` |
| b17 | `b17_lean-input-rtk` | `b17_Lean-Input-RTK` |
| b18 | `b18_lean-input-tenacity` | `b18_Lean-Input-Tenacity` |
| b19 | `b19_lean-input-pydantic` | `b19_Lean-Input-Pydantic` |

## Lean Input

The scraper-viewer slice is documented in `+docs/b11_Scraper-Viewer/`. The extractor library is Trafilatura. Do not merge that work until the parent confirms both the Grok Bot app acceptance and the Mac Cursor acceptance. After that confirmation, the coding agent may merge. A separate manual merge by the owner is not required. Linux tests are not those acceptances.

Do not clone the repository onto the Grok Bot computer or the Mac. Installed snapshots are not checkouts.

## Secrets and local state

Do not commit credentials, owner machine identifiers, virtual environments, extraction output, or install manifests from a home directory.
