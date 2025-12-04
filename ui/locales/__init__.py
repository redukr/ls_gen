from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict

LOCALES_DIR = Path(__file__).resolve().parent


def available_languages() -> Dict[str, str]:
    languages: Dict[str, str] = {}
    for path in LOCALES_DIR.glob("*.json"):
        try:
            data = load_locale(path.stem)
        except FileNotFoundError:
            continue
        display_name = data.get("_meta", {}).get("display_name", path.stem)
        languages[path.stem] = display_name
    return languages


def ensure_language(language: str) -> str:
    available = {path.stem for path in LOCALES_DIR.glob("*.json")}
    if language in available:
        return language
    if "en" in available:
        return "en"
    return sorted(available).pop() if available else language


@lru_cache(maxsize=None)
def load_locale(language: str) -> dict:
    language = ensure_language(language)
    path = LOCALES_DIR / f"{language}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Locale file not found for language: {language}")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def get_section(language: str, section: str) -> dict:
    language = ensure_language(language)
    data = load_locale(language)
    section_data = data.get(section)
    if section_data is None and language != "en":
        section_data = load_locale("en").get(section, {})
    return section_data or {}


def format_message(strings: dict, key: str, **kwargs) -> str:
    value = strings.get(key, "")
    try:
        return value.format(**kwargs)
    except Exception:
        return value
