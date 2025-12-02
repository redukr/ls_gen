import os

from ai.tools.csv_loader import load_params
from ai.tools.generator import generate_image

def generate_ai_images(prompt, csv_path, model, count):
    """
    Генерує зображення за prompt + CSV.
    Повертає список шляхів до PNG файлів.
    """

    # Завантажуємо параметри з CSV (або пустий словник)
    params = load_params(csv_path) if csv_path else None
    params_list = params or [{}]

    image_paths = []

    for i in range(count):
        # Підставляємо параметри з CSV
        param_entry = params_list[i % len(params_list)] if params_list else {}
        pr = prompt.format(**param_entry) if param_entry else prompt

        # Генеруємо зображення
        img = generate_image(pr, model_path=model)

        # Зберігаємо результат
        os.makedirs("export", exist_ok=True)
        path = f"export/ai_{i}.png"
        img.save(path)
        image_paths.append(path)

    return image_paths
