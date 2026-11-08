# Lean Input — Trafilatura vertical slice

This directory is the operator documentation for the first Lean Input tool, `lean-input-trafilatura`. The starter `client/`, `server/`, `server1/`, and `+docs/` trees are unchanged by this slice.

Canonical code lives in one place:

- `scripts/lean_input/` — shared helpers
- `skills/bot/lean-input-trafilatura/SKILL.md` — Grok Bot instructions
- `skills/cursor/lean-input-trafilatura/SKILL.md` — Mac Cursor instructions
- `tests/lean_input/` — unit, integration, installer, and packaging tests
- `packaging/` — builds independent bot and Mac candidate archives

Read in this order for a new environment: `onboarding.md`, `setup.md`, `actions.md`. Development of the slice itself is `development.md`. Replacement and removal are `update.md` and `uninstall.md`. The gate from candidate to merge is `lifecycle.md`. The manual checks that are still open are `acceptance.md`.

Nothing in this directory installs software by being read.
