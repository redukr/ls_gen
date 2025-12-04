import os
from pathlib import Path
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline


class OfflineTranslator:
    def __init__(self, model_dir: str | os.PathLike | None = None):
        if model_dir is None:
            root_dir = Path(__file__).resolve().parents[2]
            model_dir = root_dir / "ai" / "models" / "opus-mt-uk-en"
        self.model_dir = Path(model_dir).expanduser().resolve()
        self._translator = None

    def _load_translator(self):
        if self._translator is None:
            os.makedirs(self.model_dir, exist_ok=True)
            model = AutoModelForSeq2SeqLM.from_pretrained(
                "opus-mt-uk-en", cache_dir=str(self.model_dir)
            )
            tokenizer = AutoTokenizer.from_pretrained(
                "opus-mt-uk-en", cache_dir=str(self.model_dir)
            )
            self._translator = pipeline(
                "translation",
                model=model,
                tokenizer=tokenizer,
            )

    def translate(self, text: str) -> str:
        if not text or not text.strip():
            return ""
        self._load_translator()
        result = self._translator(text, max_length=512)
        return result[0]["translation_text"] if result else ""
