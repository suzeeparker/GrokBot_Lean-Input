# Setup

Prepared commands for an approved install. Reading this file does not install anything. Paths below are on the computer where the command runs. The bot computer and the Mac do not share them.

Official references checked on 2026-11-08:

- Trafilatura installation: Python 3.10 or newer. PyPI `trafilatura` 2.3.1 declares `Requires-Python: >=3.10`. Older pins remain only for old interpreters (`2.0.0` is the last release for Python 3.8 and 3.9). This slice does not install those.
- Trafilatura Python API: `extract(..., output_format="json", with_metadata=True, include_comments=False, include_tables=True)` returns a JSON string or `None`. Metadata uses `title`, `author`, and `date`. This slice maps `date` to `publication_date`.
- Direct pin used for a fresh install: `trafilatura==2.3.1` (wheel `trafilatura-2.3.1-py3-none-any.whl`, sha256 `f86bad2ee36f82884e14dee84c83aae0f0ac0127da5c65764e82f3846716b822`).
- Cursor user skills: `~/.cursor/skills/<name>/SKILL.md` with `name` and `description` frontmatter. `name` must match the folder.
- Grok Bot skills: save the skill in the Grok Bot skill library with the name `scraper-viewer`, the description from its frontmatter, and the skill file as the body. It is active once the Bot can load it by name. The library is shared by all of the owner's bots. A file write is not that step. See `Onboarding.md`.

Optional extras (`trafilatura[all]`, language detection, pycurl) are out of scope and are not installed.

## Layout

| Piece | Bot computer | Mac |
|---|---|---|
| Interpreter | `$HOME/Tools/lean-input-bot/.venv/bin/python` | `$HOME/Tools/lean-input/.venv/bin/python` |
| Helpers | `$HOME/Tools/lean-input-bot/scraper-viewer/scripts/` | `$HOME/.cursor/skills/scraper-viewer/scripts/` |
| Skill folder | `$HOME/Tools/lean-input-bot/scraper-viewer/` | `$HOME/.cursor/skills/scraper-viewer/` |
| Manifest | `$HOME/Tools/lean-input-bot/manifests/scraper-viewer.json` | `$HOME/Tools/lean-input/manifests/scraper-viewer.json` |
| Output | `$HOME/Tools/lean-input/output/` | `/Users/Shared/Repos/GrokBot_/+data/DBMSs/JSONs/d11_scraper-viewer/` |

The output directory is created on the first extraction, not by the installer, and is not removed on uninstall. The Mac path is outside the lean-input repo (`/Users/Shared/Repos/GrokBot_/lean-input`). `SCRAPER_VIEWER_OUTPUT_DIR` overrides it. A Mac run rewrites `d11_files.js` in that folder. The extractor library remains Trafilatura.

The Grok Bot computer may resolve every public name to 198.18.0.0/15 and forward it through `SAND_EGRESS_TUNNEL_PROXY_ADDR`. Extraction allows that resolved range only for `--target bot` while the variable is set. The Mac target does not. A URL that already contains a 198.18 address is refused on both.

## Development checkout tests

These commands run in a coding-agent checkout. They are not the Mac or bot install.

```sh
python3 -m venv /tmp/lean-input-dev-venv
/tmp/lean-input-dev-venv/bin/python -m pip install --disable-pip-version-check -r +skills/b10_lean_input/scripts/requirements.txt
/tmp/lean-input-dev-venv/bin/python -m unittest discover -s +skills/b00_packaging/tests -v
/tmp/lean-input-dev-venv/bin/python -m unittest discover -s +skills/b10_lean_input/tests -v
/tmp/lean-input-dev-venv/bin/python -m unittest discover -s +skills/b11_scraper-viewer/bot/tests -v
/tmp/lean-input-dev-venv/bin/python -m unittest discover -s +skills/b11_scraper-viewer/mac/tests -v
```

Optional live page, only when outbound HTTP is allowed:

```sh
/tmp/lean-input-dev-venv/bin/python +skills/b11_scraper-viewer/bot/tests/live_smoke.py https://example.com/
```

Build candidate archives after the commit exists. Replace the revision with `git rev-parse HEAD`. Do not tag a release.

```sh
python3 +skills/b00_packaging/scripts/build_candidates.py --revision "$(git rev-parse HEAD)" --out /tmp/lean-candidates
```

## Approved install test on a target computer

Use the absolute virtual-environment interpreter recorded in the manifest. From the installed helpers, the stdlib unit module can be copied from the candidate's sibling checkout only during development. On an installed machine, rerun extraction against a public URL the owner names and confirm the JSON and sidecar. The candidate archive does not include the fixture suite; the repository tests stay in the checkout.

Linux results do not establish Mac or Grok Bot app acceptance.
