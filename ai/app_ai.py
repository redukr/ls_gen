import os
from typing import Callable, List

from ai.tools.csv_loader import load_params
from ai.tools.generator import generate_image


class _SafeDict(dict):
    """A dict that leaves unknown placeholders untouched."""

    def __missing__(self, key):
        return "{" + key + "}"


def _personalize_prompt(prompt_template: str, params: dict) -> str:
    """Apply CSV params to prompt while staying friendly to Ukrainian text."""

    if not params:
        return prompt_template

    try:
        return prompt_template.format_map(_SafeDict(**params))
    except Exception:
        # If formatting fails (e.g. malformed template) fall back to original.
        return prompt_template


def _resolve_csv_path(csv_path: str | None) -> str | None:
    """Use a provided CSV/JSON path or locate it inside the config folder."""

    if not csv_path:
        return None

    if os.path.exists(csv_path):
        return csv_path

    candidate = os.path.join("config", os.path.basename(csv_path))
    if os.path.exists(candidate):
        return candidate

    return None


def generate_ai_images(
    prompt: str,
    csv_path: str | None,
    model_name: str,
    count: int,
    is_aborted: Callable[[], bool] | None = None,
) -> List[str]:
    """
    Generate a list of images with optional CSV-driven personalization.

    The helper is resilient to Ukrainian prompts (UTF-8) and will use
    personalization files when explicitly provided, resolving them inside
    the ``config`` directory if needed.
    """

    resolved_csv = _resolve_csv_path(csv_path)
    params = load_params(resolved_csv) if resolved_csv else []

    images: List[str] = []

    for i in range(count):
        if is_aborted and is_aborted():
            break

        if isinstance(params, list):
            row_params = params[i] if i < len(params) else {}
        elif isinstance(params, dict):
            row_params = params
        else:
            row_params = {}
        pr = _personalize_prompt(prompt, row_params)

        img = generate_image(pr, model_name)
        path = f"export/ai_{i+1}.png"
        img.save(path)
        images.append(path)

    return images
