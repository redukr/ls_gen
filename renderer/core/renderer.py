import os
from PIL import Image, ImageDraw, ImageFont
import sys

def resource_path(*paths):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, *paths)
    return os.path.join(os.path.abspath("."), *paths)


class CardRenderer:
    def __init__(self, template_path, frame_path, fonts_folder):
        self.template_path = template_path
        self.frame_path = frame_path
        self.fonts_folder = fonts_folder
        self.template = self.load_template()

    def load_template(self):
        import json
        if not os.path.exists(self.template_path):
            return {}
        with open(self.template_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def recolor_frame(self, frame_img, color):
        r, g, b = color
        pixels = frame_img.load()
        for y in range(frame_img.height):
            for x in range(frame_img.width):
                pr, pg, pb, pa = pixels[x, y]
                if pr > 200 and pg > 200 and pb > 200:
                    pixels[x, y] = (r, g, b, pa)
        return frame_img

    def mm_to_px(self, mm, dpi=300):
        return int((mm / 25.4) * dpi)

    def render_card(self, card_data, deck_color, bleed_mm=0):
        card_w = self.mm_to_px(40 + bleed_mm * 2)
        card_h = self.mm_to_px(62 + bleed_mm * 2)
        canvas = Image.new("RGBA", (card_w, card_h), (0,0,0,0))
        draw = ImageDraw.Draw(canvas)

        frame = Image.open(self.frame_path).convert("RGBA")
        frame = frame.resize((card_w, card_h), Image.LANCZOS)
        dc = tuple(int(deck_color[i:i+2], 16) for i in (1,3,5))
        frame = self.recolor_frame(frame, dc)
        canvas.alpha_composite(frame, (0,0))

        # ART
        if "art" in self.template:
            art_path = card_data.get("art_path", None)
            if art_path and os.path.exists(art_path):
                art = Image.open(art_path).convert("RGBA")
                tw = self.mm_to_px(self.template["art"]["w"])
                th = self.mm_to_px(self.template["art"]["h"])
                tx = self.mm_to_px(self.template["art"]["x"] + bleed_mm)
                ty = self.mm_to_px(self.template["art"]["y"] + bleed_mm)
                art = art.resize((tw, th), Image.LANCZOS)
                canvas.alpha_composite(art, (tx, ty))

        # TITLE
        if "title" in self.template:
            title = card_data.get("name", "")
            tx = self.mm_to_px(self.template["title"]["x"] + bleed_mm)
            ty = self.mm_to_px(self.template["title"]["y"] + bleed_mm)
            fs = self.template["title"]["size"]
            font_path = os.path.join(self.fonts_folder, self.template["title"]["font"])
            font = ImageFont.truetype(font_path, fs)
            draw.text((tx, ty), title, font=font, fill=(255, 255, 255, 255))

        # STATS
        if "stats" in self.template and card_data.get("type") == "unit":
            st = [
                ("ATK", "atk"),
                ("DEF", "def"),
                ("STB", "stb"),
                ("INIT", "init"),
                ("RNG", "rng"),
                ("MOVE", "move"),
            ]
            tx = self.mm_to_px(self.template["stats"]["x"] + bleed_mm)
            ty = self.mm_to_px(self.template["stats"]["y"] + bleed_mm)
            fs = self.template["stats"]["size"]
            font_path = os.path.join(self.fonts_folder, self.template["stats"]["font"])
            font = ImageFont.truetype(font_path, fs)

            offset = 0
            for label, key in st:
                val = str(card_data.get(key, ""))
                draw.text((tx, ty + offset), f"{label}: {val}", font=font, fill=(255,255,255,255))
                offset += fs + 2

        return canvas

    # ==========================================
    #   ДОБАВЛЕНІ ПРАВИЛЬНО ВИРІВНЯНІ МЕТОДИ
    # ==========================================

    def save_png(self, card_image, out_path):
        """Зберігає PNG-файл картки."""
        try:
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            card_image.save(out_path, format="PNG")
        except Exception as e:
            print(f"[Renderer] Error saving PNG: {e}")
            raise

    def save_all(self, deck, export_dir, deck_color, bleed_mm=0):
        """Генерує і зберігає всі картки."""
        for card in deck["cards"]:
            img = self.render_card(card, deck_color, bleed_mm)
            file_name = f"{card['name'].replace(' ', '_')}.png"
            out_path = os.path.join(export_dir, file_name)
            self.save_png(img, out_path)
