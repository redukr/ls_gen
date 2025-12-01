import os
from PIL import Image


class ImageLoader:
    def __init__(self):
        pass

    def load(self, path):
        """Load image safely. Returns None if file not found."""
        if not path or not os.path.exists(path):
            return None
        try:
            return Image.open(path).convert("RGBA")
        except:
            return None

    def load_scaled(self, path, width, height):
        """Load and resize image."""
        img = self.load(path)
        if img is None:
            return None
        return img.resize((width, height), Image.LANCZOS)
