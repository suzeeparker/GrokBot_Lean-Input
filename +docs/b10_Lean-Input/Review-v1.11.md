# Review of the v1.11 preparation package

The attached package `lean-input-trafilatura-review-v1.11` was inspected and not installed as-is. Its own `CHECKS.md` says no virtual environment, no Trafilatura import, no live fetch, and no Mac run. The stdlib unit tests it reported do not certify extraction.

Checked against current sources on 2026-11-08:

- PyPI `trafilatura` 2.3.1, `Requires-Python: >=3.10`, direct dependencies `certifi`, `charset_normalizer>=3.5.2`, `courlan>=1.4.0`, `htmldate>=1.11.0`, `justext>=3.0.2`, `lxml>=6.1.3`, `urllib3<3,>=2.8.0`.
- Installation documentation: Python 3.10 or newer is the current guidance. `2.0.0` is the last release for Python 3.8 and 3.9.
- `extract` accepts `output_format="json"`, `with_metadata=True`, `include_comments=False`, and `include_tables=True` (tables are already the default). The JSON metadata field for the date is `date`, not `publication_date`.
- A real 2.3.1 run on the package fixtures produced title `Community Garden Report`, author `Alex Example`, and date `2024-05-02` for `normal.html`. `missing-metadata.html` returned JSON null for those three fields. `empty.html` returned `None`. `imperfect.html` still returned the article text and title `Garden`.
- The same release turned a short "Enable JavaScript" page into ordinary text. A success flag on that output would be wrong.
- `include_tables=True` kept table cells as flattened text (`Kale`, `Beans`), so a warning must say flattened or omitted, not that tables always disappear.
- Cursor's documented user skill path remains `~/.cursor/skills/<name>/SKILL.md`.
- Grok Bot's documented skill save is the in-app private skill library plus per-Bot enablement. Copying a file is not registration.

## Reused

- Public-address checks, pinned connect, standard ports, no credentials, no HTTPS downgrade, size and time limits.
- Exclusive create so an existing output or sidecar is not overwritten.
- A metrics sidecar so the serialized JSON length is not stored inside the JSON it measures.
- The four HTML fixtures, plus the split between injected unit tests and real extraction tests.
- Separate bot and Mac homes, and absolute interpreters.

## Rejected or corrected

- The package duplicated bot and Mac trees and asked a person to keep them identical. This slice keeps one canonical helper and checks the built archives for equal helper bytes.
- There was no `install` / `uninstall` / `explain` / `do` parser, no onboarding path for an unregistered skill, and no ownership manifest, checksum, or rollback.
- The setup stopped when the destination directory existed at all, so a valid preexisting virtual environment could not be reused. It also had no protection against a silent Trafilatura upgrade. This slice reuses a valid environment and a 2.x Trafilatura, and refuses other majors.
- HTML and text lengths lived in the result JSON. They were not a self-count, but the contract the owner asked for is the sidecar. All three measurements are in the sidecar. The result JSON is the extraction record.
- `value or None` collapses every falsy metadata value. Strings are stripped, and a non-string is omitted with a warning instead of being stringified.
- Challenge pages were only a standing warning. Short challenge text is now an error and is not returned as the article. Paywall language stays in the text and adds a warning. Nothing is bypassed.
- The user agent advertised preparation version 1.11. The helper now identifies `lean-input-trafilatura/candidate` and does not pretend to be a browser.
- Integration tests were present and unrun. They are run here against 2.3.1. A Linux freeze of transitive wheels is recorded as evidence, not as a Mac lock. `charset_normalizer`, `lxml`, and `regex` publish platform wheels.
- The package is not vendored into this repository.

## Still unresolved by Linux tests

Mac Cursor discovery, the Grok Bot private-skill enablement, and any live page the owner cares about on those computers. See `Acceptance.md`.
