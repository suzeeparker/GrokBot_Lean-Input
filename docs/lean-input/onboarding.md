# Onboarding coordinator

Use this file when `lean-input-trafilatura` is not registered yet. You are the coordinator, not the skill. Do not wait for the skill to appear before following these steps, and do not invent a slash command.

The owner already approved preparing this candidate and opening a pull request. The owner has not approved installing it on the Grok Bot computer or the Mac. Stop and ask before the first install on either machine. Do not install on both machines in one approval.

## Do not

- Do not clone the GitHub repository onto the bot computer or the Mac. Copy or download the candidate archive instead. The archive has no `.git` directory.
- Do not merge. The coding agent may merge only after the parent explicitly confirms both the real Grok Bot app acceptance and the Mac Cursor acceptance. Linux tests are neither confirmation.
- Do not install silently, upgrade a preexisting tool, or overwrite a file the manifest does not own.
- Do not put an owner name, email, or machine id into a skill or helper.
- Do not start a watcher or an automatic update.

## 1. Identify the archive

Use the archive whose name contains `bot` only on the Grok Bot computer, and the archive whose name contains `mac` only on the Mac. Read `CANDIDATE.json`. Record `source_revision`, `trafilatura_pin`, and `stable_release` (it must be false). Refuse the archive if it contains a `.git` directory.

## 2. Choose the base interpreter

Ask for the absolute path of Python 3.10 or newer. On the machine, a version check is:

```sh
"$BASE_PYTHON" -c 'import sys,ssl,venv; assert sys.version_info >= (3, 10); print(sys.executable); print(ssl.OPENSSL_VERSION)'
```

If that fails, stop. Do not install Python, Homebrew, or a compiler yourself.

## 3. Show the plan

Unpack the archive outside the home tool directories. From that unpacked directory:

```sh
"$BASE_PYTHON" "$UNPACKED/runtime/install_runtime.py" install \
  --target bot \
  --home "$HOME" \
  --source-root "$UNPACKED" \
  --python "$BASE_PYTHON"
```

Use `--target mac` for the Mac archive. Exit 3 with no new files means the plan is waiting for approval. Read the file list, virtual-environment action, and dependency action to the owner.

## 4. Install only after approval

Repeat the command with `--approve`. Add `--update` only if the owner also approved replacing managed files that differ from this candidate. A compatible preexisting Trafilatura 2.x is reused. Any other major version aborts without replacement.

The manifest records source revision, interpreter, dependency version, ownership, and checksums. If the install fails midway, the helper rolls back files and a virtual environment created by that attempt. It does not delete a virtual environment that was already there.

## 5. Register on the Grok Bot computer

Writing `SKILL.md` under `$HOME/Tools/lean-input-bot/` does not register a skill.

Official Grok Bot documentation (Skills and routines, read 2026-11-08) says a skill is saved by asking the Bot to save the process, and a private skill is enabled per Bot under Connect apps, the connected count, Private skills. This installer does not call a network API. No public registration endpoint was verified for this slice; do not invent one.

While you are the already-running Bot, save a private skill:

- name: `lean-input-trafilatura`
- description: the `description` frontmatter of the installed skill text
- body: the installed `SKILL.md`

Then tell the owner to enable it for this Bot if you cannot see that control. Ask for the skill by name and confirm it answers `explain` without changing files. Until that works, report the runtime as installed and the skill as not active.

## 6. Discover on the Mac

Cursor loads `$HOME/.cursor/skills/lean-input-trafilatura/SKILL.md` as a user skill (Cursor skills documentation, read 2026-11-08). The installer places that file. Ask the owner to open Customize, Skills, and confirm the name is listed. Do not turn on Sync Skills for Cloud Agents unless the owner asks. Do not claim the skill is active before it is visible.

## 7. Check the helper

Use the absolute virtual-environment interpreter from the manifest. Run the unit and integration tests from `docs/setup.md` only after install approval, and record the actual Trafilatura version. A pass on one computer does not count for the other.

## 8. Hand back

Report the candidate revision, manifest path, dependency version, what was reused, what was created, and which registration or discovery check is still open. Stop there. Acceptance steps are in `docs/acceptance.md`.
