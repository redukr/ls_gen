from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
import os

# ─────────────────────────────────────────────
# ПРАВИЛЬНИЙ PDF EXPORTER ДЛЯ LS_gen
# ─────────────────────────────────────────────

def export_pdf_from_list(image_list, output_path):
    """
    Створює PDF з переліку PNG/JPG зображень.
    Кожне зображення → нова сторінка.
    Підтримує LS_gen і PyInstaller.
    """

    if not image_list:
        raise ValueError("Список зображень порожній — нема що експортувати.")

    # Створюємо директорію, якщо її нема
    folder = os.path.dirname(output_path)
    if folder:
        os.makedirs(folder, exist_ok=True)

    # PDF документ
    pdf = canvas.Canvas(output_path, pagesize=letter)
    page_w, page_h = letter

    for img_path in image_list:
        if not os.path.exists(img_path):
            print(f"[PDF WARNING] Файл не існує і буде пропущено: {img_path}")
            continue

        try:
            img = ImageReader(img_path)
            pdf.drawImage(img, 0, 0, width=page_w, height=page_h, preserveAspectRatio=True)
            pdf.showPage()
        except Exception as e:
            print(f"[PDF ERROR] Помилка {img_path}: {e}")

    pdf.save()
    print(f"PDF збережено: {output_path}")


# ─────────────────────────────────────────────
# Псевдонім, якщо хтось викличе стару функцію
# ─────────────────────────────────────────────

def export_pdf(images, path):
    """Старе ім'я функції. Залишається для сумісності."""
    return export_pdf_from_list(images, path)