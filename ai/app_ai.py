from LS_gen.ai.tools.csv_loader import load_params
from LS_gen.ai.tools.generator import generate_image
import os

def generate_ai_images(prompt, csv_path, model, count):
    """
    Генерує зображення за prompt + CSV.
    Повертає список шляхів до PNG файлів.
    """

    # Завантажуємо параметри з CSV (або пустий словник)
    params = load_params(csv_path) if csv_path else [{}]

    image_paths = []

    for i in range(count):
        # Підставляємо параметри з CSV
        pr = prompt.format(**params[i]) if params and params[i] else prompt

        # Генеруємо зображення
        img = generate_image(pr, model)

        # Зберігаємо результат
        os.makedirs("export", exist_ok=True)
        path = f"export/ai_{i}.png"
        img.save(path)
        image_paths.append(path)

    return image_paths