from __future__ import annotations

import sys
from pathlib import Path


def application_base_dir() -> Path:
    """Return directory where logs and resources should be stored.

    Mirrors the logic used for locating files near the executable or source.
    """
    if hasattr(sys, "_MEIPASS"):
        return Path(sys.argv[0]).resolve().parent
    return Path(__file__).resolve().parent.parent
