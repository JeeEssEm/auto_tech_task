"""
Универсальный парсер текста из разных форматов
"""
import os
import datetime
from typing import Dict, Any

from .exceptions import ExtractorNotFound
from .extractors.text import TextExtractor
from .extractors.json import JsonExtractor
from .extractors.office import OfficeExtractor
from .extractors.audio import AudioExtractor
from .extractors.video import VideoExtractor

class UniversalParser:
    def __init__(self, use_whisper=True, whisper_model="tiny"):
        self.use_whisper = use_whisper

        self.extractors = {
            'txt': TextExtractor(),
            'md': TextExtractor(),
            'json': JsonExtractor(),
            'docx': OfficeExtractor(),

            'mp3': AudioExtractor(use_whisper=use_whisper, model_name=whisper_model),
            'wav': AudioExtractor(use_whisper=use_whisper, model_name=whisper_model),
            'flac': AudioExtractor(use_whisper=use_whisper, model_name=whisper_model),
            'ogg': AudioExtractor(use_whisper=use_whisper, model_name=whisper_model),

            'mp4': VideoExtractor(use_whisper=use_whisper, model_name=whisper_model),
            'flv': VideoExtractor(use_whisper=use_whisper, model_name=whisper_model),
            'mov': VideoExtractor(use_whisper=use_whisper, model_name=whisper_model),
            'mkv': VideoExtractor(use_whisper=use_whisper, model_name=whisper_model),
            'avi': VideoExtractor(use_whisper=use_whisper, model_name=whisper_model),
            'wmv': VideoExtractor(use_whisper=use_whisper, model_name=whisper_model),
            'webm': VideoExtractor(use_whisper=use_whisper, model_name=whisper_model),
        }

    def parse(self, file_path: str, original_filename: str = None) -> Dict[str, Any]:
        """
        Главный метод: принимает путь к локальному файлу (например из S3)
        и оригинальное имя файла (опционально) для метаданных.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл не найден: {file_path}")

        actual_filename = original_filename or os.path.basename(file_path)
        file_ext = self._get_file_extension(actual_filename)

        extractor = self._get_extractor(file_ext)

        # Извлекаем текст и метаданные
        text, metadata = extractor.extract(file_path, actual_filename)

        # Если файл не умеет отдавать дату создания (напр., видео/аудио),
        # берем время создания файла на диске в качестве фоллбэка.
        if "created_time" not in metadata:
            try:
                ctime = os.path.getctime(file_path)
                metadata["created_time"] = datetime.datetime.fromtimestamp(ctime).isoformat()
            except Exception:
                metadata["created_time"] = None

        return {
            "text": text,
            "metadata": metadata
        }

    def _get_file_extension(self, filename: str) -> str:
        ext = os.path.splitext(filename)[1].lower()
        return ext[1:] if ext.startswith('.') else ext

    def _get_extractor(self, file_ext: str):
        # Если формат не знаем, по умолчанию парсим как текстовый файл

        extractor = self.extractors.get(file_ext)
        if not extractor:
            raise ExtractorNotFound()

        return extractor


def parse(file_path: str, original_filename: str = None, use_whisper=True, whisper_model="tiny") -> Dict[str, Any]:
    parser = UniversalParser(use_whisper=use_whisper, whisper_model=whisper_model)
    return parser.parse(file_path, original_filename)
