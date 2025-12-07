import requests


class OfflineTranslator:
    def __init__(self, api_url="https://libretranslate.de/translate"):
        self.api_url = api_url

    def translate(self, text: str) -> str:
        if not text.strip():
            return ""

        try:
            response = requests.post(
                self.api_url,
                data={
                    "q": text,
                    "source": "uk",
                    "target": "en",
                    "format": "text"
                },
                timeout=10
            )

            data = response.json()

            if "translatedText" not in data:
                return f"[ERROR] Некоректна відповідь API: {data}"

            return data["translatedText"]

        except Exception as e:
            return f"[ERROR] Переклад недоступний: {e}"
