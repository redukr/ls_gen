# generate_structure.py
import os

OUTPUT_FILE = "structure.txt"

def write_structure(base_path, output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        for root, dirs, files in os.walk(base_path):

            # Пропускаємо службові папки
            if "__pycache__" in root or ".git" in root or "venv" in root:
                continue

            level = root.replace(base_path, "").count(os.sep)
            indent = "    " * level
            folder_name = os.path.basename(root)

            # Папка
            if folder_name == "":
                folder_name = os.path.basename(base_path)

            f.write(f"{indent}{folder_name}/\n")

            # Файли в папці
            subindent = "    " * (level + 1)
            for file in files:
                # Пропускаємо зайве
                if file.endswith(".pyc") or file.startswith("."):
                    continue
                f.write(f"{subindent}{file}\n")

    print(f"[OK] Структура проєкту збережена у файл: {output_file}")


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    write_structure(base_dir, OUTPUT_FILE)
