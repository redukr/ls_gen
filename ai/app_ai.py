import os
from typing import Callable, List

import torch
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

        # Work on a copy so we don't mutate cached CSV/JSON rows across calls.
        if isinstance(row_params, dict):
            row_params = dict(row_params)
        else:
            row_params = {}

        # -------------------------------------------------
        # Переклад CSV-полів, якщо обрана мова ≠ українська
        # -------------------------------------------------
        if language != "Українська" and isinstance(row_params, dict):
            # Prefer explicit English value if it exists to avoid over-translating.
            if row_params.get("name_en"):
                row_params.setdefault("name", row_params["name_en"])

            translator = OfflineTranslator()
            for k, v in row_params.items():
                if isinstance(v, str):
                    if k.endswith("_en"):
                        continue
                    try:
                        row_params[k] = translator.translate(v)
                    except Exception:
                        pass

        chosen_prompt = (
            row_params.get("prompt")
            or row_params.get("promt")
            or prompt
        )
        pr = _personalize_prompt(chosen_prompt, row_params)
        effective_style = row_params.get("style_hint") or style_hint
        pr = _enrich_prompt_with_params(pr, row_params, style_hint=effective_style)

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


def generate_previews(
    prompt: str,
    csv_path: str | None,
    model_name: str,
    *,
    count: int = 8,
    width: int,
    height: int,
    style_hint: str = STYLE_HINT,
    language: str = "Українська",
    steps: int = 7,
    row_indices: List[int] | None = None,
) -> List[dict]:
    """Generate lightweight preview images with preserved seeds.

    Each returned item contains the preview path alongside the seed and
    parameters needed to recreate the image at higher quality later on.
    """

    resolved_csv = _resolve_csv_path(csv_path)
    params = load_params(resolved_csv) if resolved_csv else []

    previews: List[dict] = []

    for i in range(count):
        if isinstance(params, list):
            param_idx = row_indices[i] if row_indices and i < len(row_indices) else i
            row_params = params[param_idx] if param_idx < len(params) else {}
        elif isinstance(params, dict):
            row_params = params
        else:
            row_params = {}

        if isinstance(row_params, dict):
            row_params = dict(row_params)
        else:
            row_params = {}

        if language != "Українська" and isinstance(row_params, dict):
            if row_params.get("name_en"):
                row_params.setdefault("name", row_params["name_en"])

            translator = OfflineTranslator()
            for k, v in row_params.items():
                if isinstance(v, str):
                    if k.endswith("_en"):
                        continue
                    try:
                        row_params[k] = translator.translate(v)
                    except Exception:
                        pass

        chosen_prompt = (
            row_params.get("prompt")
            or row_params.get("promt")
            or prompt
        )
        enriched_prompt = _personalize_prompt(chosen_prompt, row_params)
        enriched_prompt = _enrich_prompt_with_params(
            enriched_prompt,
            row_params,
            style_hint=row_params.get("style_hint") or style_hint,
        )

        seed = torch.randint(0, 2**32 - 1, (1,)).item()
        img = generate_image(
            enriched_prompt,
            model_name,
            width=width,
            height=height,
            steps=steps,
            seed=seed,
        )
        os.makedirs("export", exist_ok=True)
        path = f"export/preview_{i+1}.png"
        img.save(path)

        previews.append(
            {
                "path": path,
                "seed": seed,
                "prompt": enriched_prompt,
                "model": model_name,
                "width": width,
                "height": height,
                "style_hint": style_hint,
                "params": row_params,
            }
        )

    return previews


def finalize_preview(preview: dict, *, steps: int = 30) -> str:
    """Regenerate a preview with higher quality using the same seed."""

    prompt = preview.get("prompt", "")
    model_name = preview.get("model", "")
    width = int(preview.get("width", 664))
    height = int(preview.get("height", 1040))
    seed = preview.get("seed")

    img = generate_image(
        prompt,
        model_name,
        width=width,
        height=height,
        steps=steps,
        seed=seed,
    )

    os.makedirs("export", exist_ok=True)
    file_seed = seed if seed is not None else "seedless"
    path = f"export/final_{file_seed}.png"
    if os.path.exists(path):
        base, ext = os.path.splitext(path)
        suffix = 1
        while os.path.exists(f"{base}_{suffix}{ext}"):
            suffix += 1
        path = f"{base}_{suffix}{ext}"
    img.save(path)
    return path
