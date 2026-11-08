# Lifecycle

The candidate, the two real installs, and the merge are separate gates. Passing one does not pass the next.

## 1. Candidate tests in the coding checkout

Run the unit, fixture, installer, and packaging tests in an isolated virtual environment. Optionally run one public live smoke and record the URL and the measured result. Build bot and Mac archives from the exact commit. The archives are candidates: no stable release and no git tag.

Linux results do not establish the Grok Bot app or the Mac.

## 2. Bot and Mac installs, only after separate approval

The parent arranges the real Grok Bot app install and the Mac Cursor install. Each uses its candidate archive, not a git clone. The onboarding coordinator in `onboarding.md` is how an unregistered skill gets installed. Record each environment's revision, Trafilatura version, commands, and failures on their own. Do not install from this cloud checkout onto the owner's Mac or the owner's bot runtime.

## 3. Manual acceptance

The owner, or the parent acting for the owner, runs `acceptance.md` on the Grok Bot app and on Mac Cursor. Both lists have to pass. A pass on one machine is not a pass on the other.

## 4. Merge

There is no requirement that the owner merge by hand.

The coding agent may merge after the parent explicitly confirms that both acceptance lists passed. Until that confirmation, the pull request stays unmerged. This candidate's pull request is not that confirmation.

Do not force-push, bypass hooks, or rewrite published history. A destructive history rewrite needs a separate approval from the parent. Commit subjects follow `CONTRIBUTING.md`.

## 5. After the merge commit exists

1. Read the exact merged revision from GitHub. Do not assume it equals the candidate commit.
2. Rebuild the bot and Mac archives from that revision. Do not clone onto the bot computer or the Mac to do it.
3. Compare the rebuild with the tested candidate using `packaging/compare_candidates.py`. Report every differing path, especially `runtime/`.
4. Retest the merged revision in the coding checkout.
5. Reinstall on the bot computer and the Mac only with a new approval, using the rebuilt archives, then rerun the acceptance lists.
6. Do not start a watcher or an automatic updater.

## Pull request during development

The owner allowed a pull request for this slice before the acceptance installs. Opening the pull request is not a merge and not an acceptance.
