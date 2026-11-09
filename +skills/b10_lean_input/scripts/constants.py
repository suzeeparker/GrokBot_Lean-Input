"""Shared constants for the Trafilatura vertical slice.

Stdlib only. Imported by the extractor, the installer, and action dispatch.
"""

COMPONENT = "lean-input-trafilatura"
TRAFILATURA_PIN = "2.3.1"
PYTHON_MIN = (3, 10)
COMPATIBLE_MAJOR = 2
USER_AGENT = "lean-input-trafilatura/candidate (+https://trafilatura.readthedocs.io/)"

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

RUNTIME_FILES = (
    "constants.py",
    "extract_url.py",
    "scrape_options.py",
    "actions.py",
    "install_runtime.py",
    "requirements.txt",
)
