# Acceptance checklist

Linux tests in the coding checkout are not these checks. Do not mark an item from a checkout log. The parent confirms both lists before anyone merges. The coding agent is allowed to merge after that confirmation and is not allowed to merge before it. The owner does not have to merge by hand.

Installed snapshots are not git checkouts. Do not clone the repository onto either computer to perform these steps.

## Grok Bot app

- [ ] The bot candidate archive was transferred without a git clone, and `CANDIDATE.json` `source_revision` was recorded.
- [ ] The onboarding plan was shown and approved before files changed.
- [ ] The manifest lists checksums, the interpreter path, Trafilatura's version, and whether the virtual environment was created or reused.
- [ ] A preexisting compatible tool was not upgraded. An unmanaged file was not overwritten.
- [ ] The private skill `scraper-viewer` was saved in the Grok Bot skill library and the Bot can load it by name. The library is shared by all of the owner's bots. A file under `~/Tools` was not treated as activation.
- [ ] In the Grok Bot app, `scraper-viewer explain` changes nothing and reports the bot paths and the installed version.
- [ ] `scraper-viewer https://example.com/` or another ordinary public URL the owner chooses writes JSON and a metrics sidecar, reports the three measured character counts, and does not paste raw HTML into chat.
- [ ] An invalid URL, a timeout, a non-HTML response, or an empty extraction fails with a clear status. A challenge or paywall is not bypassed.
- [ ] The output path is not overwritten when the file already exists.
- [ ] Uninstall shows the managed list, deletes only those files after confirmation, and leaves the shared virtual environment, output, and unrelated skills.
- [ ] A second install of the same revision writes nothing.

## Mac Cursor

- [ ] The Mac candidate archive was transferred without a git clone, and its `source_revision` was recorded separately from the bot.
- [ ] The onboarding plan was shown and approved before files changed.
- [ ] Python is `$HOME/Tools/lean-input/.venv/bin/python`. Helpers are `$HOME/.cursor/skills/scraper-viewer/scripts/`. Output is `/Users/Shared/Repos/GrokBot_/+data/DBMSs/JSONs/d11_scraper-viewer/`, and `d11_files.js` there lists the JSON files.
- [ ] Customize, Skills, lists `scraper-viewer`. Sync Skills for Cloud Agents was not enabled unless the owner asked.
- [ ] `explain` is read-only and names the Mac paths, not the bot paths.
- [ ] A public URL extraction writes JSON and a sidecar. Counts are measured. Raw HTML is not pasted into chat.
- [ ] Invalid URL, non-HTML, empty extraction, and existing-output refusal fail clearly. Challenges and paywalls are not bypassed.
- [ ] Uninstall preserves the shared virtual environment, output, and unrelated skills.
- [ ] The bot result was not used as evidence for these Mac items.

## After both lists

The parent confirms both lists. Then the coding agent may merge and follow the post-merge rebuild in `lifecycle.md`. Until that message, the pull request stays open and unmerged.
