from PIL import Image

def cut_center_transparent(base_img, overlay_img):
    """
    Накладає overlay_img по центру на base_img.
    Якщо overlay_img = None — повертає base_img як є.
    """

    if not overlay_img:
        return base_img

    # Якщо шляху нема — повертаємо початкове
    if isinstance(overlay_img, str):
        try:
            overlay = Image.open(overlay_img).convert("RGBA")
        except:
            return base_img
    else:
        overlay = overlay_img

    base = base_img.convert("RGBA")

    # Центруємо оверлей
    x = (base.width - overlay.width) // 2
    y = (base.height - overlay.height) // 2

    base.paste(overlay, (x, y), overlay)
    return base
