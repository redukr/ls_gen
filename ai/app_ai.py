from ai.tools.csv_loader import load_params
from ai.tools.generator import generate_image
import os

def generate_ai_images(prompt, csv_path, model_name, count):
    from ai.tools.csv_loader import load_params
    from ai.tools.generator import generate_image

    # Завантаження CSV
    params = load_params(csv_path) if csv_path else []

    images = []

    for i in range(count):

        if params and i < len(params):
            try:
                pr = prompt.format(**params[i])
            except:
                pr = prompt
        else:
            pr = prompt

        img = generate_image(pr, model_name)
        path = f"export/ai_{i+1}.png"
        img.save(path)
        images.append(path)

    return images
