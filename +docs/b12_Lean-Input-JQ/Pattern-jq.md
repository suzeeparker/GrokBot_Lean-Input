# Pattern for a later lean-input-jq

This file is the pattern only. `lean-input-jq` is not implemented, and neither are the other Lean Input tools.

## What stays the same

1. One canonical helper directory in the repository. Bot and Mac skills contain environment instructions, not a second copy of the helper that can drift.
2. `+skills/b00_packaging/scripts/build_candidates.py` copies that helper into two archives and fails if the helper bytes differ. Archives are not git checkouts.
3. The installed skill name stays `lean-input-<tool>` with no `b##` prefix. The repository folder uses the prefix (`b11_lean-input-trafilatura`, and later `b12_lean-input-jq`). Frontmatter `name` matches the installed skill name. The description says when to use the skill.
4. The skill interprets `install`, `uninstall`, `explain`, and `do`. `do` is the default when the first standalone word is not an action. Parsing lives in one helper.
5. An onboarding document can install the skill before it is registered. On the bot, save it in the Grok Bot skill library. It is active once the Bot can load it by name, and that library is shared by all of the owner's bots. On the Mac, Cursor discovery is `~/.cursor/skills/<name>/SKILL.md`, confirmed in Customize.
6. Install checks the interpreter, an existing tool, and file ownership. It reuses a compatible tool, installs a missing pinned tool only inside the approved environment, and does not upgrade or replace otherwise.
7. A manifest records source revision, ownership, dependency or tool version, and checksums. Failed installs roll back files they created. Uninstall is confirmed and removes only matching managed files. Shared virtual environments, other skills, and user data stay.
8. `explain` is read-only. `do` offers setup when the runtime is missing and does not install itself.
9. Source data is untrusted. Results that drop information say so. Measured character counts are reported only when they were measured.
10. Tests cover the parser, refusal and idempotence under a temporary home, the real tool on fixtures, and failure cases. A Linux pass is not acceptance on the other computer.
11. Candidates are untagged. Merge waits for the parent's confirmation that bot-app and Mac acceptance both passed. The agent may merge at that point. After merge, rebuild from the exact revision and compare.

## What would change for jq

- The tool is the `jq` binary, not a Python package. The version check is `jq --version` using an absolute path, not a virtual environment import.
- Input is local JSON or JSON text the owner already has, not a public page fetch. There is no HTTP client, redirect policy, or HTML sidecar.
- `do` selects fields or a filter the owner names. It does not invent a filter when the request is ambiguous, and it does not shell-interpolate file contents.
- Output is filtered JSON written without overwrite, plus a character count of the input document and the output document in a sidecar.
- The shared Mac virtual environment is irrelevant unless a later Python helper appears. Uninstall must not remove `~/Tools/lean-input/.venv` just because a jq skill is leaving.
- A preexisting `jq` on the machine is reused when its version is in the accepted range. A missing binary is installed only by the method the owner approved, and is not upgraded in place.
- Tests use fixture JSON files, invalid JSON, and a refusal to overwrite. They do not need Trafilatura.

Build that tool as its own skill pair after this Trafilatura slice has been accepted. Do not add it to this candidate.
