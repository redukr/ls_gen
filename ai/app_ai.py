import os
from typing import Callable, List
from renderer.widgets.translator import OfflineTranslator

from ai.tools.csv_loader import load_params
from ai.tools.generator import generate_image


class _SafeDict(dict):
    """A dict that leaves unknown placeholders untouched."""

    def __missing__(self, key):
        return "{" + key + "}"


STYLE_HINT = (
    "Cinematic board-game art, cohesive color grading, well-defined subject,"
    " tactical atmosphere"
)


def _personalize_prompt(prompt_template: str, params: dict) -> str:
    """Apply CSV params to prompt while staying friendly to Ukrainian text."""

    if not params:
        return prompt_template

    try:
        return prompt_template.format_map(_SafeDict(**params))
    except Exception:
        # If formatting fails (e.g. malformed template) fall back to original.
        return prompt_template


def _enrich_prompt_with_params(prompt: str, params: dict, *, style_hint: str = STYLE_HINT) -> str:
    """Limit prompt enrichment to "name" and "type" fields.

    Only the identifying fields are appended to keep images unified without
    overloading the model with extra CSV details.
    """

    base_prompt = prompt.strip()

    name = params.get("name") if params else None
    type_value = params.get("type") if params else None

    fragments = []
    if name:
        fragments.append(f'call-sign "{name}"')
    if type_value:
        fragments.append(f"type: {type_value}")

    descriptor = "; ".join(fragments)

    # Always add the shared style hint to each generated prompt so every image
    # keeps the same board-game aesthetic even when personalized by CSV data.
    if descriptor:
        return f"{base_prompt} | Card brief: {descriptor}. {style_hint}."

    return f"{base_prompt}. {style_hint}."


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
    width: int,
    height: int,
    is_aborted: Callable[[], bool] | None = None,
    *,
    style_hint: str = STYLE_HINT,
    language: str = "Українська",   # ← ДОДАТИ ЦЕ
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
            
        # -------------------------------------------------
        # Переклад CSV-полів, якщо обрана мова ≠ українська
        # -------------------------------------------------
        if language != "Українська" and isinstance(row_params, dict):
            translator = OfflineTranslator()
            for k, v in row_params.items():
                if isinstance(v, str):
                    try:
                        row_params[k] = translator.translate(v)
                    except Exception:
                        pass

        
        pr = _personalize_prompt(prompt, row_params)
        pr = _enrich_prompt_with_params(pr, row_params, style_hint=style_hint)

        img = generate_image(
            pr,
            model_name,
            width=width,
            height=height,
        )
        path = f"export/ai_{i+1}.png"
        img.save(path)
        images.append(path)

    return images
