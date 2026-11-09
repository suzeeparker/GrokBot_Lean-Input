"""Shared constants for the scraper-viewer slice.

The extractor library is Trafilatura. Stdlib only. Imported by the extractor,
the installer, and action dispatch.
"""

import os
from pathlib import Path

COMPONENT = "scraper-viewer"
DEPRECATED_COMPONENT = "lean-input-trafilatura"
TRAFILATURA_PIN = "2.3.1"
PYTHON_MIN = (3, 10)
COMPATIBLE_MAJOR = 2
USER_AGENT = "scraper-viewer/candidate (+https://trafilatura.readthedocs.io/)"
MAC_OUTPUT_DIR = "/Users/Shared/Repos/GrokBot_/lean-input/client1/+data/DBMSs/JSONs/d11_scraper-viewer"
MAC_OUTPUT_ENV = "SCRAPER_VIEWER_OUTPUT_DIR"

MAX_BYTES = 5 * 1024 * 1024
SOCKET_TIMEOUT_SECONDS = 10
MAX_REDIRECTS = 5
TOTAL_DEADLINE_SECONDS = 40
MAX_URL_LENGTH = 2048

LOSS_WARNING = (
    "Extraction is heuristic. Tables may be flattened or omitted. "
    "Links, formatting, and browser-only content can be missing. "
    "Character counts are Unicode code points, not bytes or tokens. "
    "JSON is structure, not a shorter copy of the page."
)

def output_directory(target, home=None):
    """Return the directory that receives JSON output for ``target``.

    The Mac setting defaults to the d11 scraper-viewer data folder.
    ``SCRAPER_VIEWER_OUTPUT_DIR`` overrides that default. The bot target
    keeps ``~/Tools/lean-input/output``.
    """
    if target == "mac":
        override = os.environ.get(MAC_OUTPUT_ENV, "").strip()
        if override:
            return Path(override).expanduser()
        return Path(MAC_OUTPUT_DIR)
    root = Path(home).expanduser() if home else Path.home()
    return root / "Tools" / "lean-input" / "output"


RUNTIME_FILES = (
    "constants.py",
    "extract_url.py",
    "scrape_options.py",
    "actions.py",
    "install_runtime.py",
    "requirements.txt",
)
