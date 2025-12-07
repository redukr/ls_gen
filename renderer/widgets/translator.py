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

            # Перевірка статусу
            if response.status_code != 200:
                return f"[ERROR] API недоступне: {response.status_code} {response.text}"

            # Спроба розпарсити JSON
            try:
                data = response.json()
            except Exception:
                return f"[ERROR] Некоректна відповідь API (не JSON): {response.text[:200]}"

            if "translatedText" not in data:
                return f"[ERROR] Некоректна відповідь API: {data}"

            return data["translatedText"]

        except Exception as e:
            return f"[ERROR] Переклад недоступний: {e}"