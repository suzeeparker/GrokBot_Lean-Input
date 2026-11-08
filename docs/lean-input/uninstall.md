# Uninstall

Uninstall removes the managed Trafilatura skill files for one target. It asks first.

```sh
"$PYTHON" "$RUNTIME/actions.py" --target bot --home "$HOME" --message "uninstall"
```

Use `--target mac` and the Mac interpreter and runtime on the Mac. The command prints each manifest path with the action it would take. Nothing is deleted.

When the owner agrees to that list, and only then:

```sh
"$PYTHON" "$RUNTIME/actions.py" --target bot --home "$HOME" --message "uninstall" --confirm YES
```

`--confirm YES` is a flag the agent adds after agreement. A sentence that merely contains "yes" is not confirmation.

## Removed

- Helper files under the target runtime directory whose checksum still matches the manifest
- The skill text file whose checksum still matches
- The onboarding copy installed beside the helpers, when its checksum matches
- The manifest, when every listed file was removed or was already absent
- Empty directories that the manifest recorded, after those files are gone

## Kept

- The shared virtual environment (`~/Tools/lean-input-bot/.venv` or `~/Tools/lean-input/.venv`)
- Trafilatura and every other package in that environment
- `$HOME/Tools/lean-input/output/` and any other user data
- Files that are not in the manifest, including notes dropped beside the skill
- Other skills
- Managed files whose checksum no longer matches (reported as skipped; exit 4; the manifest keeps those entries)
- A Grok Bot private-skill registration. Removing that registration is a separate confirmation in the Bot app, because deleting a private skill removes it for every Bot

If there is no manifest, uninstall reports `nothing-managed` and deletes nothing. Running it twice after a full removal is the same result.
