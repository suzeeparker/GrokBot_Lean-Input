# Candidate test evidence — Linux checkout

Recorded 2026-11-08 in America/New_York. This is the coding-checkout run. It is not a Grok Bot app install and it is not a Mac Cursor install. Nothing was installed into an owner home directory.

## Interpreter and direct dependency

- Python 3.12.3, GCC 13.3.0, OpenSSL 3.0.13 30 Jan 2024
- Trafilatura 2.3.1, which matches the fresh-install pin
- PyPI requires Python >=3.10. The official installation page says 3.10 or newer
- Integration and the real installer test both imported `trafilatura` 2.3.1

The Linux resolution of the direct pin was:

```text
babel==2.18.0
certifi==2026.10.23
charset-normalizer==3.5.2
courlan==1.4.0
dateparser==1.5.0
htmldate==1.11.0
jusText==3.0.2
lxml==6.1.3
lxml_html_clean==0.4.6
python-dateutil==4.0.0
pytz==2026.6
regex==2026.11.8
tld==0.13.2
trafilatura==2.3.1
tzdata==2026.6
tzlocal==5.4.5
urllib3==2.8.0
```

`charset-normalizer`, `lxml`, and `regex` are platform wheels. Do not treat this list as a Mac lock. The installer pins only `trafilatura==2.3.1` and records whatever that machine resolves.

## Command

The checkout recipe is the same install into a fresh virtual environment. The recorded process used `/tmp/lean-tf-venv/bin/python` after `python3 -m venv` and `pip install -r +skills/b10_lean_input/scripts/requirements.txt`.

```sh
/tmp/lean-tf-venv/bin/python -m unittest discover -s +skills/b00_packaging/tests
/tmp/lean-tf-venv/bin/python -m unittest discover -s +skills/b10_lean_input/tests
/tmp/lean-tf-venv/bin/python -m unittest discover -s +skills/b11_scraper-viewer/tests
```

Result after the `+skills` and `+docs` move, Python 3.12.3: 31 tests, OK.

- `+skills/b00_packaging/tests`: 1 test
- `+skills/b10_lean_input/tests`: 21 tests
- `+skills/b11_scraper-viewer/tests`: 9 tests The run includes action parsing, read-only explain, a missing-runtime refusal, fixture extraction, Unicode counts, challenge and paywall handling, HTTP failure cases, staged install idempotence, unmanaged-file refusal, incompatible-tool refusal, rollback, a real temporary virtual environment with `trafilatura==2.3.1`, confirmed uninstall that keeps that environment, and candidate archive equality.

## Live smoke

Command:

```sh
/tmp/lean-tf-venv/bin/python +skills/b11_scraper-viewer/tests/live_smoke.py https://example.com/
```

Exit 0. Decoded HTML was not printed.

| Field | Value |
|---|---|
| requested_url | `https://example.com/` |
| final_url | `https://example.com/` |
| status | success |
| title | Example Domain |
| author | null |
| publication_date | null |
| text | This domain is for use in documentation examples without needing permission. This is not a service; avoid relying on it for testing and monitoring purposes. |
| decoded_html_characters | 577 |
| extracted_text_characters | 156 |
| serialized_json_characters | 632 |
| unit | unicode_code_points |
| serialized length matches the JSON file | true |

The text is shorter than the HTML because boilerplate and markup were dropped. That is a measurement, not a savings claim. Title text from the page is not repeated in this particular extraction.

## Egress-tunnel retest

Python 3.12.3 on this checkout, after allowing 198.18.0.0/15 only for `--target bot` when `SAND_EGRESS_TUNNEL_PROXY_ADDR` is set. 34 tests, OK: 1 packaging, 24 shared, 9 Trafilatura. The same `https://example.com/` smoke, without that variable, stayed a direct public connection: decoded HTML 577, extracted text 156, serialized JSON 632. No tunnel warning was added.

## Refusal exit code and registration wording

Python 3.12.3. 36 tests, OK: 1 packaging, 26 shared, 9 Trafilatura. `http://localhost/` now exits 2 and still writes the error JSON. A fetch failure still exits 1. The same `https://example.com/` smoke, with no tunnel variable, remained decoded HTML 577, extracted text 156, serialized JSON 632.

## Not done

- No skill was registered in the Grok Bot app
- No file was written under an owner Mac home
- No merge
- Mac wheels were not installed or tested
- `Acceptance.md` remains unchecked
