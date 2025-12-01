import torch
from diffusers import (
    StableDiffusionPipeline,
    StableDiffusionXLPipeline,
    EulerAncestralDiscreteScheduler
)
import os

pipe = None
current_model_path = None
current_model_type = None


def load_model(model_type, model_path):
    """Завантажує SD1.5 або SDXL вручну за model_type та model_path."""

    global pipe, current_model_path, current_model_type

    # Якщо модель змінена → перезавантаження
    if pipe is None or current_model_path != model_path or current_model_type != model_type:
        current_model_path = model_path
        current_model_type = model_type
        pipe = None

        print(f"[INFO] Завантаження моделі: {model_path} ({model_type})")

        dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        device = "cuda" if torch.cuda.is_available() else "cpu"

        # ---------------------------
        # SDXL МОДЕЛЬ
        # ---------------------------
        if model_type == "sdxl":
            pipe = StableDiffusionXLPipeline.from_pretrained(
                model_path,
                torch_dtype=dtype,
                use_safetensors=True,
                variant="fp16",
                safety_checker=None
            )

            # Оптимізація для RTX 3060 (6GB)
            pipe.to("cuda")
            pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config)


        # ---------------------------
        # SD1.5 МОДЕЛЬ
        # ---------------------------
        elif model_type == "sd15":
            pipe = StableDiffusionPipeline.from_pretrained(
                model_path,
                torch_dtype=dtype,
                safety_checker=None
            )

            # Оптимізація (легша модель)
            pipe.to(device)

        else:
            raise ValueError(f"Невідомий тип моделі: {model_type}")

    return pipe



def generate_image(
        prompt,
        width=768,
        height=1088,
        model_type="sdxl",
        model_path=None,
        steps=25,
        seed=None,
        pipe=None
    ):
    """
    Універсальна функція генерації:
    - SD1.5 / SDXL
    - ручний вибір моделі
    """

    if pipe is None:
        pipe = load_model(model_type, model_path)

    # Seed
    if seed is None:
        seed = torch.randint(0, 2**32 - 1, (1,)).item()
    generator = torch.manual_seed(seed)

    # Генерація
    image = pipe(
        prompt=prompt,
        negative_prompt="low quality, jpeg artifacts, blurry, distorted, watermark",
        num_inference_steps=steps,
        width=width,
        height=height,
        generator=generator,
        guidance_scale=5.0,
    ).images[0]

    return image
