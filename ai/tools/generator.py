import torch
from diffusers import (
    StableDiffusionPipeline,
    StableDiffusionXLPipeline,
    DPMSolverMultistepScheduler
)
import os

pipe = None
current_model_path = None
current_model_type = None

torch.set_float32_matmul_precision("medium")


# Мапа моделей
AVAILABLE_MODELS = {
    "RealVisXL (SDXL)": ("sdxl", "ai/models/realvisxl"),
    "SDXL Base 1.0": ("sdxl", "ai/models/stable-diffusion-xl-base-1.0"),
    "DreamShaperXL": ("sdxl", "ai/models/dreamshaperxl"),
    "JuggernautXL": ("sdxl", "ai/models/juggernautxl"),
}


# ============================================================
#                 LOAD MODEL (RTX 3060 OPTIMIZED)
# ============================================================
def load_model(model_type, model_path):
    global pipe, current_model_path, current_model_type

    # Якщо модель змінюється — перезавантажуємо повністю
    if pipe is None or current_model_path != model_path or current_model_type != model_type:

        current_model_path = model_path
        current_model_type = model_type
        pipe = None

        print(f"[INFO] Завантаження моделі: {model_path} ({model_type})")

        device = torch.device("cuda")
        dtype = torch.float16

        # -----------------------------
        # SDXL PIPELINE
        # -----------------------------
        if model_type == "sdxl":
            pipe = StableDiffusionXLPipeline.from_pretrained(
                model_path,
                torch_dtype=dtype,
                use_safetensors=True,
                variant="fp16"
            ).to(device)

        # -----------------------------
        # SD 1.5 PIPELINE
        # -----------------------------
        elif model_type == "sd15":
            pipe = StableDiffusionPipeline.from_pretrained(
                model_path,
                torch_dtype=dtype,
                use_safetensors=True
            ).to(device)

        else:
            raise ValueError(f"Unknown model type: {model_type}")

        # =================================================
        #                 RTX 3060 ОПТИМІЗАЦІЇ
        # =================================================

        print("[OPT] Applying RTX 3060 optimizations...")

        # 1. Attention slicing — економить VRAM
        pipe.enable_attention_slicing()
        print("[OPT] attention slicing enabled")

        # 2. VAE slicing — зменшує навантаження на VRAM
        try:
            pipe.vae.enable_slicing()
            print("[OPT] VAE slicing enabled")
        except:
            print("[OPT WARNING] VAE slicing unavailable")

        # 3. VAE tiling — дуже важливо для SDXL на 6GB VRAM
        try:
            pipe.vae.enable_tiling()
            print("[OPT] VAE tiling enabled")
        except:
            print("[OPT WARNING] VAE tiling unavailable")

        # 4. scheduler DPM++ 2M Karras — найкращий баланс швидкість/якість
        pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
        print("[OPT] Scheduler: DPM++ 2M")

        # 5. torch.compile — дає +10–20% швидкості навіть на Windows
        try:
            # torch.compile на Windows дуже повільний під час warmup → вимикаємо
            print("[OPT] torch.compile disabled (Windows safe mode)")
        except Exception as e:
            print(f"[OPT WARNING] torch.compile failed: {e}")

        # 6. Перший прогін для прогріву (warmup)
        try:
            print("[INFO] Warmup...")
            _ = pipe(
                prompt="warmup test",
                num_inference_steps=1,
                width=512,
                height=512
            )
        except:
            print("[INFO] Warmup skipped (safe)")

    return pipe



# ============================================================
#                     GENERATE IMAGE
# ============================================================
DEFAULT_NEGATIVE_PROMPT = (
    "low quality, jpeg artifacts, blurry, distorted, watermark, text, logo, signature,"
    " extra limbs, extra fingers, mutation, disfigured, poorly drawn hands,"
    " malformed anatomy, long neck, duplicate body"
)


def generate_image(
    prompt,
    model_name,
    width=664,
    height=1040,
    steps=25,
    seed=None,
    negative_prompt: str | None = None,
):
    """
    Генерує одне зображення, використовуючи модель з AVAILABLE_MODELS.
    """

    if model_name not in AVAILABLE_MODELS:
        raise ValueError(f"Модель '{model_name}' не знайдена у AVAILABLE_MODELS")

    model_type, model_path = AVAILABLE_MODELS[model_name]

    pipe = load_model(model_type, model_path)

    # Seed
    if seed is None:
        seed = torch.randint(0, 2**32 - 1, (1,)).item()
    generator = torch.manual_seed(seed)

    # --- Генерація ---
    image = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt or DEFAULT_NEGATIVE_PROMPT,
        num_inference_steps=steps,
        width=width,
        height=height,
        generator=generator,
        guidance_scale=5.0,
    ).images[0]

    return image
