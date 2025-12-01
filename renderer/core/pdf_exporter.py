import os
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

class PDFExporter:
    def __init__(self, dpi=300, margin_mm=20):
        self.dpi = dpi
        self.margin_mm = margin_mm

    def mm_to_px(self, mm_value):
        return int((mm_value / 25.4) * self.dpi)

    def export_pdf(self, folder, output_path, card_width_mm=40, card_height_mm=62, bleed_mm=0):
        """
        Правильний метод: приймає шлях до директорії з PNG-файлами.
        """

        if not os.path.isdir(folder):
            raise FileNotFoundError(f"Директорію не знайдено: {folder}")

        # Збираємо всі PNG-файли у стабільному порядку
        image_paths = []
        for f in sorted(os.listdir(folder)):
            if f.lower().endswith(".png"):
                full_path = os.path.join(folder, f)
                if os.path.isfile(full_path):
                    image_paths.append(full_path)

        if not image_paths:
            raise FileNotFoundError(f"У директорії немає PNG-файлів:\n{folder}")

        # Розміри карток
        page_width, page_height = A4
        margin = self.margin_mm * mm

        card_w_pt = (card_width_mm + 2 * bleed_mm) * mm
        card_h_pt = (card_height_mm + 2 * bleed_mm) * mm

        # Готуємо PDF
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(output_path, pagesize=A4)

        x = margin
        y = page_height - margin - card_h_pt

        cards_per_row = max(1, int((page_width - margin * 2) // card_w_pt))
        cards_per_col = max(1, int((page_height - margin * 2) // card_h_pt))

        current_col = 0
        rows_used = 0

        # Додаємо кожну картку
        for img_path in image_paths:
            temp_img = Image.open(img_path)
            temp_img_path = img_path + "_tmp_for_pdf.png"
            temp_img.save(temp_img_path, dpi=(self.dpi, self.dpi))

            c.drawImage(
                temp_img_path,
                x, y,
                width=card_w_pt,
                height=card_h_pt,
                preserveAspectRatio=True,
                mask="auto"
            )

            os.remove(temp_img_path)

            current_col += 1

            if current_col >= cards_per_row:
                current_col = 0
                rows_used += 1
                x = margin
                y -= card_h_pt

                if rows_used >= cards_per_col:
                    c.showPage()
                    y = page_height - margin - card_h_pt
                    rows_used = 0
            else:
                x += card_w_pt

        c.save()

        return output_path
