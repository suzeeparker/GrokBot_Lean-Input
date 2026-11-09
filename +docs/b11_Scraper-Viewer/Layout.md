# Layout

## Folder prefix

The `b##` prefix is lowercase in `+skills/` and in `+docs/`. The tool name in a docs folder stays capitalized: `+docs/b11_Scraper-Viewer`. `+skills/b11_scraper-viewer` stays lowercase.

## Delivered platform folders

```text
+skills/b11_scraper-viewer/bot/
  SKILL.md
  scripts/
  tests/
  docs/
+skills/b11_scraper-viewer/mac/
  SKILL.md
  scripts/
  tests/
  docs/
```

Copying `bot/` or `mac/` includes the helper code, the tests, and the docs required to install and run that platform. Those scripts do not import `+skills/b10_lean_input`. A virtual environment is not inside the folder. Trafilatura is installed into the managed venv outside the skill.

`win/` is the planned third platform name. Windows is not supported. There is no `win` folder and no Windows package.

`mac` means macOS. Cursor discovers `~/.cursor/skills/scraper-viewer/`. Another macOS coding agent can use that same folder. The directory name `.cursor` is Cursor's discovery path, not the platform name.

## Shared code

`+skills/b10_lean_input/scripts/` is the canonical helper source and the template for a later tool. Edit shared behavior there, then run `+skills/b00_packaging/scripts/sync_platform_copies.py`. That refreshes `scripts/`, `docs/`, and the common tests in `bot/` and `mac/`. It does not overwrite `SKILL.md` or `scripts/run.py`.

The tradeoff: one canonical copy avoids drift, and the delivered folders stay self-contained. A check fails if `bot/scripts` and `mac/scripts` disagree with the canonical files on the shared modules. `run.py` may differ by platform. Keeping the canonical tree out of the install means an installed skill does not need the repository.

`b10` is not a separate product and does not gain new tool behavior here.

## Installed paths

| | Previous `379d1ef` | This candidate |
|---|---|---|
| Bot helpers | `~/Tools/lean-input-bot/runtime/scraper-viewer/` | `~/Tools/lean-input-bot/scraper-viewer/scripts/` |
| Bot skill text | `~/Tools/lean-input-bot/skill-source/scraper-viewer/SKILL.md` | `~/Tools/lean-input-bot/scraper-viewer/SKILL.md` |
| Mac helpers | `~/Tools/lean-input/runtime/scraper-viewer/` | `~/.cursor/skills/scraper-viewer/scripts/` |
| Mac skill | `~/.cursor/skills/scraper-viewer/SKILL.md` only | `~/.cursor/skills/scraper-viewer/` with scripts and docs |
| Venv | unchanged, outside the skill | unchanged, outside the skill |
| Bot output | `~/Tools/lean-input/output/` | same |
| Mac output | `/Users/Shared/Repos/GrokBot_/+data/DBMSs/JSONs/d11_scraper-viewer/` | same. `SCRAPER_VIEWER_OUTPUT_DIR` still overrides it |

`lean-input-trafilatura` remains a deprecated invocation alias for one release.

## Migration

Do not change a machine that is still on `379d1ef` until this candidate is reviewed and accepted.

An approved install of this candidate:

- Writes the new skill folder.
- Removes a previous managed file only when its checksum still matches the manifest.
- Leaves a changed file where it is and does not overwrite it.
- Does not delete the virtual environment, Trafilatura, output JSON, or `d11_files.js`.
- Replaces `SKILL.md` only when `--update` is passed, because that path already exists and its bytes differ.

Candidate zip files in this checkout are not a GitHub release. Publishing a release archive is still pending.

## Tests

```sh
python3 -m unittest discover -s +skills/b00_packaging/tests
python3 -m unittest discover -s +skills/b10_lean_input/tests
python3 -m unittest discover -s +skills/b11_scraper-viewer/bot/tests
python3 -m unittest discover -s +skills/b11_scraper-viewer/mac/tests
```

The bot and mac test directories run the same common checks against that platform's `scripts/`. Each directory also has its own skill text checks.
