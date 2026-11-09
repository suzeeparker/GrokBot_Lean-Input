"""Launch scraper-viewer from the bot skill folder.

Helpers live in this directory. This file does not import a sibling package.
"""

from __future__ import annotations

from pathlib import Path
import sys

PLATFORM = "bot"
sys.path.insert(0, str(Path(__file__).resolve().parent))

import actions  # noqa: E402


if __name__ == "__main__":
    sys.exit(actions.main())
