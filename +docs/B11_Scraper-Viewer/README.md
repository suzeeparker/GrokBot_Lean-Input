# scraper-viewer

This directory is the operator documentation for `scraper-viewer`. The extractor library is Trafilatura 2.3.1. The installed skill name has no `b##` prefix. `lean-input-trafilatura` is a deprecated invocation alias for one release. The starter `client/`, `server/`, and `server1/` trees are separate from this slice. The Mac viewer is `client1/c11_scraper-viewer-app/`.

Repository layout:

- `+skills/b10_lean_input/scripts/` — shared helpers
- `+skills/b11_scraper-viewer/bot/SKILL.md` — Grok Bot instructions
- `+skills/b11_scraper-viewer/cursor/SKILL.md` — Mac Cursor instructions
- `+skills/b11_scraper-viewer/scripts/run.py` — thin entry that calls the shared helpers
- `+skills/b00_packaging/scripts/` — candidate archive builder
- `+docs/b12_Lean-Input-JQ/Pattern-jq.md` — pattern only; jq is not implemented

Installed names do not use the `b##` prefix. The installed skill remains `scraper-viewer`.

Read in this order for a new environment: `Onboarding.md`, `Setup.md`, `Actions.md`. Development of the slice itself is `Development.md`. Replacement and removal are `Update.md` and `Uninstall.md`. The gate from candidate to merge is `Lifecycle.md`. The manual checks that are still open are `Acceptance.md`.

Nothing in this directory installs software by being read.
