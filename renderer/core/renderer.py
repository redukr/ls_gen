import os

from PIL import Image, ImageDraw, ImageFont

from renderer.core.paths import ABSOLUTE_PATH

class CardRenderer:
    """
    Спрощений, але повністю робочий CardRenderer_v2
    Працює з card_data та template (layout).
    Підтримує:
    - арт
    - заголовок
    - опис
    - стати (atk, def, stb)
    - шрифти з assets/fonts
    - іконки з assets/icons
    """

    def __init__(self, template: dict):
        self.template = template

        # Шляхи ресурсів
        self.fonts_path = ABSOLUTE_PATH("assets/fonts")
        self.icons_path = ABSOLUTE_PATH("assets/icons")
        self.frames_path = ABSOLUTE_PATH("assets/frames/frame.png")

        # Завантаження шрифтів
        self.font_title = ImageFont.truetype(os.path.join(self.fonts_path, "LS_font.ttf"), 48)
        self.font_desc = ImageFont.truetype(os.path.join(self.fonts_path, "LS_font.ttf"), 32)
        self.font_stats = ImageFont.truetype(os.path.join(self.fonts_path, "LS_font.ttf"), 40)

    # -------------------------------------------------
    # ГОЛОВНИЙ РЕНДЕР-ФУНКЦІОНАЛ
    # -------------------------------------------------
    def render(self, card_data: dict):
        W = self.template["canvas_width"]
        H = self.template["canvas_height"]

        # Створюємо полотно
        card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(card)

        # -------------------------------------------------
        # 1. ФОН / РАМКА
        # -------------------------------------------------
        if os.path.exists(self.frames_path):
            frame = Image.open(self.frames_path).convert("RGBA")
            frame = frame.resize((W, H))
            card.alpha_composite(frame, (0, 0))

        # -------------------------------------------------
        # 2. АРТ
        # -------------------------------------------------
        if "img" in card_data and card_data["img"]:
            art = Image.open(card_data["img"]).convert("RGBA")

            x, y, w, h = self._get_area("image")
            art = art.resize((w, h))
            card.alpha_composite(art, (x, y))

        # -------------------------------------------------
        # 3. TITLE
        # -------------------------------------------------
        if "title" in card_data:
            x, y, w, h = self._get_area("title")
            draw.text((x, y), card_data["title"], font=self.font_title, fill=(255, 255, 255, 255))

        # -------------------------------------------------
        # 4. DESCRIPTION
        # -------------------------------------------------
        if "description" in card_data:
            x, y, w, h = self._get_area("description")
            draw.text((x, y), card_data["description"], font=self.font_desc, fill=(220, 220, 220, 255))

        # -------------------------------------------------
        # 5. СТАТИ
        # -------------------------------------------------
        stats_map = {
            "atk": "atk.png",
            "def": "def.png",
            "stb": "stb.png"
        }

        for key, icon_file in stats_map.items():
            if key in card_data:
                x, y, w, h = self._get_area(key)
                icon_path = os.path.join(self.icons_path, icon_file)

                if os.path.exists(icon_path):
                    icon = Image.open(icon_path).convert("RGBA").resize((w, h))
                    card.alpha_composite(icon, (x, y))

                # малюємо число поверх іконки
                draw.text((x + w + 10, y), str(card_data[key]), font=self.font_stats, fill=(255, 255, 255, 255))

        return card

    # -------------------------------------------------
    # ДОПОМІЖНА ФУНКЦІЯ: ЗОНА З LAYOUT
    # -------------------------------------------------
    def _get_area(self, key):
        area = self.template.get(key, None)
        if not area:
            return (0, 0, 0, 0)
        return (area["x"], area["y"], area["w"], area["h"])
