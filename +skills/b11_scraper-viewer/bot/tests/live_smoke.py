"""Optional public fetch. Not part of unittest discovery.

Usage:
  /path/to/venv/bin/python +skills/b11_scraper-viewer/tests/live_smoke.py https://example.com/
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

_HERE = Path(__file__).resolve()
_PACKAGE = _HERE.parents[1]
if (_PACKAGE / "scripts" / "extract_url.py").is_file():
    sys.path.insert(0, str(_PACKAGE / "scripts"))
else:
    sys.path.insert(0, str(_HERE.parents[3] / "+skills" / "b10_lean_input" / "scripts"))

import extract_url  # noqa: E402


def main(argv):
    url = argv[1] if len(argv) > 1 else "https://example.com/"
    result, html = extract_url.process(url)
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "live.json"
        metrics = extract_url.write_outputs(result, output, html, False)
        written = output.read_text(encoding="utf-8")
    report = {
        "requested_url": result["requested_url"],
        "final_url": result["final_url"],
        "status": result["status"],
        "error": result["error"],
        "title": result["title"],
        "author": result["author"],
        "publication_date": result["publication_date"],
        "warnings": result["warnings"],
        "text": result["text"],
        "metrics": metrics,
        "serialized_matches_file": metrics["serialized_json_characters"] == len(written),
        "decoded_html_was_not_printed": True,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
