import requests

class OfflineTranslator:
    def __init__(self):
        self.api_url = "https://api.mymemory.translated.net/get"

    def translate(self, text: str) -> str:
        if not text.strip():
            return ""

        try:
            response = requests.get(
                self.api_url,
                params={
                    "q": text,
                    "langpair": "uk|en"
                },
                timeout=10
            )

            data = response.json()

            if "responseData" not in data:
                raise ValueError(f"Некоректна відповідь API: {data}")

            return data["responseData"]["translatedText"]

        except Exception as e:
            raise RuntimeError(f"Переклад недоступний: {e}") from e
