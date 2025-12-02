from __future__ import annotations

import sys
import os
from pathlib import Path

# ─────────────────────────────────────────────
# BASE DIRECTORY
# ─────────────────────────────────────────────

def application_base_dir() -> Path:
    """
    Повертає базову директорію проєкту.
    Працює як у звичайному Python, так і в PyInstaller EXE.
    """
    # Якщо запущено як EXE (PyInstaller встановлює _MEIPASS)
    if hasattr(sys, "_MEIPASS"):
        return Path(sys.argv[0]).resolve().parent

    # Якщо запущено як Python-скрипт
    return Path(__file__).resolve().parent.parent


# ─────────────────────────────────────────────
# ABSOLUTE PATH RESOLVER
# ─────────────────────────────────────────────

def ABSOLUTE_PATH(relative_path: str) -> str:
    """
    Формує абсолютний шлях до файлу відносно кореня ls_gen.
    Підтримує EXE та Python.
    """
    base = application_base_dir()
    return str(base.joinpath(relative_path))
