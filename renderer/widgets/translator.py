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
                raise RuntimeError(
                    f"API недоступне: {response.status_code} {response.text}"
                )

            # Спроба розпарсити JSON
            try:
                data = response.json()
            except Exception as exc:
                raise ValueError(
                    f"Некоректна відповідь API (не JSON): {response.text[:200]}"
                ) from exc

            if "translatedText" not in data:
                raise ValueError(f"Некоректна відповідь API: {data}")

            return data["translatedText"]

        except Exception as e:
            raise RuntimeError(f"Переклад недоступний: {e}") from e