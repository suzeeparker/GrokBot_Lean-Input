"""Thin repository entry for lean-input-trafilatura.

Shared code stays in +skills/b10_lean_input/scripts. This file only adds that
directory to sys.path and forwards to actions.main. An installed runtime runs
the copied helpers by absolute path; it does not use this relative import.
"""

from __future__ import annotations

from pathlib import Path
import sys

SHARED = Path(__file__).resolve().parents[2] / "b10_lean_input" / "scripts"
sys.path.insert(0, str(SHARED))

import actions  # noqa: E402


if __name__ == "__main__":
    sys.exit(actions.main())
