# Update

An update replaces managed files with a newer candidate. It is not a silent upgrade.

1. Build or download the candidate for the exact source revision. Do not clone the repository onto the target computer.
2. Run install without `--approve` and without `--update`. If every managed checksum already matches, the later approved run reports `unchanged` and writes nothing.
3. If a managed file differs, the command stops and names the file. Show that list to the owner.
4. After the owner approves the replacement, rerun with `--approve --update`. Unmanaged files still block the run and are not overwritten.
5. `--update` does not change Trafilatura. A missing install can add the pinned 2.3.1 release. A present 2.x release stays at that version. A different major version aborts.
6. The manifest records the new source revision and the new checksums. The previous file bytes are held only for the duration of the attempt so a failed update can restore them. They are not kept as a second installed copy after success.
7. On the bot computer, file replacement does not edit the private skill. If the skill body should change, save the new body through the Grok Bot skill library and enable it again. On the Mac, Cursor reads the replaced `SKILL.md`; confirm the skill still appears under Customize, Skills.
8. Do not start a watcher, cron job, or login item to pull later revisions.

Compare a post-merge rebuild with the tested candidate using `packaging/compare_candidates.py` before installing the rebuilt archive. Matching runtime hashes and a new source revision still deserve a retest. Do not assume the merged tree equals the candidate.
