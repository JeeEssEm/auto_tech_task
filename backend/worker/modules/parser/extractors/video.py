"""
Парсер для видео файлов - извлекает аудио и транскрибирует
"""
import os
import tempfile
import subprocess
from .base import BaseExtractor

class VideoExtractor(BaseExtractor):
    def __init__(self, use_whisper=True, model_name="tiny"):
        super().__init__()
        self.use_whisper = use_whisper
        self.model_name = model_name

    def extract(self, file_path: str, original_filename: str = None):
        if not self.use_whisper:
            raise RuntimeError("Видео парсер отключен. Включите use_whisper=True")

        metadata = self._get_basic_metadata(original_filename)

        # Резервируем имя временного файла (только для аудио дорожки)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
            audio_path = tmp.name

        try:
            cmd = [
                'ffmpeg', '-i', file_path, '-vn', '-acodec', 'pcm_s16le',
                '-ar', '16000', '-ac', '1', '-y', audio_path
            ]
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            if process.returncode != 0:
                raise RuntimeError(f"FFmpeg ошибка при извлечении аудио: {process.stderr[:200]}")

            if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 100:
                raise RuntimeError("Не удалось извлечь аудиодорожку (файл пуст или не создан)")

            # Транскрибируем извлеченное аудио
            from .audio import AudioExtractor
            audio_extractor = AudioExtractor(
                use_whisper=self.use_whisper,
                model_name=self.model_name
            )
            text, audio_metadata = audio_extractor.extract(audio_path, original_filename)

            metadata["duration"] = audio_metadata.get("duration", 0)
            return text, metadata

        finally:
            if os.path.exists(audio_path):
                os.unlink(audio_path)
