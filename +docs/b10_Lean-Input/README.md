# Lean Input — Trafilatura vertical slice

This directory is the operator documentation for the first Lean Input tool, `lean-input-trafilatura`. The starter `client/`, `server/`, and `server1/` trees are separate from this slice.

Repository layout:

- `+skills/b10_lean_input/scripts/` — shared helpers
- `+skills/b11_lean-input-trafilatura/bot/SKILL.md` — Grok Bot instructions
- `+skills/b11_lean-input-trafilatura/cursor/SKILL.md` — Mac Cursor instructions
- `+skills/b11_lean-input-trafilatura/scripts/run.py` — thin entry that calls the shared helpers
- `+skills/b00_packaging/scripts/` — candidate archive builder
- `+docs/b12_Lean-Input-JQ/Pattern-jq.md` — pattern only; jq is not implemented

Installed names do not use the `b##` prefix. The installed skill remains `lean-input-trafilatura`.

Read in this order for a new environment: `Onboarding.md`, `Setup.md`, `Actions.md`. Development of the slice itself is `Development.md`. Replacement and removal are `Update.md` and `Uninstall.md`. The gate from candidate to merge is `Lifecycle.md`. The manual checks that are still open are `Acceptance.md`.

Nothing in this directory installs software by being read.
