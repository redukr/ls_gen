import os

from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

def export_pdf_from_list(image_list, output_path):
    """
    Створює PDF-файл з переліку PNG-зображень.
    Кожна картка — окрема сторінка PDF.
    Працює з LS_gen.
    """

    if not image_list:
        raise ValueError("Список зображень порожній — нема що експортувати.")

    # Переконуємось, що директорія існує
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Формуємо PDF
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
            print(f"[PDF ERROR] Помилка при обробці {img_path}: {e}")

    pdf.save()
    print(f"PDF збережено: {output_path}")


def export_pdf(image_list, output_path):
    """Backward-compatible wrapper for PDF export."""

    return export_pdf_from_list(image_list, output_path)
