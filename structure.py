# generate_structure.py
import os

OUTPUT_FILE = "structure.txt"

def write_structure(base_path, output_file):

    # Абсолютний шлях до директорії моделей
    MODELS_PATH = os.path.abspath(os.path.join(base_path, "ai", "models"))

    # Папки, у які не можна заходити взагалі
    SKIP_DIRS = {"__pycache__", ".git", "venv", "clean_venv", ".vscode"}

    with open(output_file, "w", encoding="utf-8") as f:
        for root, dirs, files in os.walk(base_path):

            abs_root = os.path.abspath(root)

            # Видаляємо службові директорії з обходу
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

            # Відносний шлях
            rel_root = os.path.relpath(abs_root, base_path)
            level = 0 if rel_root == "." else rel_root.count(os.sep)
            indent = "    " * level

            # --- Якщо директорія = models ---
            if abs_root == MODELS_PATH:

                f.write(f"{indent}models/\n")

                # Показуємо тільки моделі (перший рівень)
                subindent = "    " * (level + 1)
                for d in dirs:
                    f.write(f"{subindent}{d}/\n")

                # Забороняємо заглиблення у моделі
                dirs[:] = []
                continue

            # --- Якщо ми всередині models/... (глибше) ---
            if abs_root.startswith(MODELS_PATH + os.sep):
                dirs[:] = []   # не заходити в підпапки
                files[:] = []  # не показувати файли
                continue

            # --- Стандартний запис структури ---
            folder = os.path.basename(abs_root) if rel_root != "." else os.path.basename(base_path)
            f.write(f"{indent}{folder}/\n")

            subindent = "    " * (level + 1)
            for file in files:
                if file.startswith(".") or file.endswith(".pyc"):
                    continue
                f.write(f"{subindent}{file}\n")

    print(f"[OK] Структура збережена у:", output_file)


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    write_structure(base_dir, OUTPUT_FILE)
