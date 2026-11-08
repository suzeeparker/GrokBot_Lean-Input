# Contributing

## Commit subjects

Use Robin's date in the `America/New_York` time zone. The date tag is five digits: the last digit of the year, the two-digit month, and the two-digit day. 8 November 2026 is `61108`. 29 May 2026 is `60529`.

The subject starts with `.(` and has no closing parenthesis. The sequence is the nth commit already using that date tag in this repository, including commits that are only on the remote, plus one. It is two digits.

```text
.(61108.05_Add Trafilatura skills
```

That subject is the whole first line: `.(`, the date tag, `.`, the sequence, `_`, then the comment. Do not add `)`.

Before choosing the sequence, read `git log` for the date tag on the local branch and on `origin`. Do not reuse a number. The next subject after `.(61108.04_...` on 8 November 2026 is `.(61108.05_...`. A later commit the same local day uses `06`, then `07`.

A commit body after a blank line is optional. The existing history uses the subject line alone. Keep the subject itself in this form either way.

Do not amend, rebase, or force-push a commit that has been pushed in order to rename it. Published history stays as it is. A destructive history rewrite needs an explicit approval from the parent first. Do not do one because a subject looks inconsistent.

## Lean Input

The Trafilatura slice is documented in `docs/lean-input/`. Do not merge that work until the parent confirms both the Grok Bot app acceptance and the Mac Cursor acceptance. After that confirmation, the coding agent may merge. A separate manual merge by the owner is not required. Linux tests are not those acceptances.

Do not clone the repository onto the Grok Bot computer or the Mac. Installed snapshots are not checkouts.

## Secrets and local state

Do not commit credentials, owner machine identifiers, virtual environments, extraction output, or install manifests from a home directory.
