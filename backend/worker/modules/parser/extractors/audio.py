"""
Парсер для аудио файлов с использованием Whisper
"""
from .base import BaseExtractor

class AudioExtractor(BaseExtractor):
    def __init__(self, use_whisper=True, model_name="large"):
        super().__init__()
        self.use_whisper = use_whisper
        self.model_name = model_name
        self._whisper_model = None

    def extract(self, file_path: str, original_filename: str = None):
        if not self.use_whisper:
            raise RuntimeError("Аудио парсер отключен. Включите use_whisper=True")

        metadata = self._get_basic_metadata(original_filename)

        try:
            import whisper
        except ImportError:
            raise ImportError("Whisper не установлен. Установите: pip install openai-whisper")

        # Ленивая загрузка
        if self._whisper_model is None:
            self._whisper_model = whisper.load_model(self.model_name)

        # Whisper умеет напрямую читать пути файлов с диска
        result = self._whisper_model.transcribe(
            file_path,
            language='ru',
            task='transcribe',
            fp16=False,
            beam_size=5,
            best_of=5,
            temperature=0.0,
            compression_ratio_threshold=2.4,
            no_speech_threshold=0.6,
            condition_on_previous_text=False,
            word_timestamps=False,
            verbose=False
        )

        text = result["text"].strip()
        metadata["duration"] = result.get("duration", 0)  # Специфично для медиа

        return text, metadata
