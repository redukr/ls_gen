import requests

class OfflineTranslator:
    def __init__(self):
        self.api_url = "https://api.mymemory.translated.net/get"

    def translate(self, text: str, langpair: str = "uk|en") -> str:
        if not text.strip():
            return ""

        try:
            response = requests.get(
                self.api_url,
                params={
                    "q": text,
                    "langpair": langpair
                },
                timeout=10
            )

            data = response.json()

            if "responseData" not in data:
                raise ValueError(f"Некоректна відповідь API: {data}")

            return data["responseData"]["translatedText"]

        except Exception as e:
            raise RuntimeError(f"Переклад недоступний: {e}") from e

    def translate_name(self, name: str) -> str:
        """Перекладає назву з української на англійську"""
        return self.translate(name, "uk|en")
