from __future__ import annotations

import sys
from pathlib import Path


def application_base_dir() -> Path:
    """Return directory where logs and resources should be stored.

    Mirrors the logic used for locating files near the executable or source.
    """
    if hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    # Go up to the repository root (renderer/core -> renderer -> project root)
    return Path(__file__).resolve().parent.parent.parent


def ABSOLUTE_PATH(*parts: str) -> str:
    """Build an absolute path inside the application directory."""

    return str(application_base_dir().joinpath(*parts))
