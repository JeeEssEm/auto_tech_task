"""
Универсальный парсер текста из разных форматов с использованием Docling
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
    # Поддерживаемые модели Whisper: tiny, base, small, medium, large
    WHISPER_MODELS = ["tiny", "base", "small", "medium", "large"]
    
    def __init__(self, use_whisper=True, whisper_model="base"):
        """
        Args:
            use_whisper: Включить транскрипцию аудио/видео через Whisper
            whisper_model: Модель Whisper (tiny, base, small, medium, large)
        """
        if whisper_model not in self.WHISPER_MODELS:
            raise ValueError(
                f"Неизвестная модель Whisper: {whisper_model}. "
                f"Доступные модели: {', '.join(self.WHISPER_MODELS)}"
            )
        
        self.use_whisper = use_whisper
        self.whisper_model = whisper_model

        self.extractors = {
            # Текстовые форматы
            'txt': TextExtractor(),
            'md': TextExtractor(),
            
            # JSON
            'json': JsonExtractor(),
            
            # Документы (обрабатывает docling)
            'docx': OfficeExtractor(),
            'pptx': OfficeExtractor(),
            'xlsx': OfficeExtractor(),
            'pdf': OfficeExtractor(),
            'doc': OfficeExtractor(),
            'xls': OfficeExtractor(),
            'ppt': OfficeExtractor(),
            
            # Аудио файлы (с Whisper)
            'mp3': AudioExtractor(use_whisper=use_whisper, model_name=whisper_model),
            'wav': AudioExtractor(use_whisper=use_whisper, model_name=whisper_model),
            'flac': AudioExtractor(use_whisper=use_whisper, model_name=whisper_model),
            'ogg': AudioExtractor(use_whisper=use_whisper, model_name=whisper_model),
            'aac': AudioExtractor(use_whisper=use_whisper, model_name=whisper_model),
            'm4a': AudioExtractor(use_whisper=use_whisper, model_name=whisper_model),
            'wma': AudioExtractor(use_whisper=use_whisper, model_name=whisper_model),
            
            # Видео файлы (с Whisper для аудиодорожки)
            'mp4': VideoExtractor(use_whisper=use_whisper, model_name=whisper_model),
            'flv': VideoExtractor(use_whisper=use_whisper, model_name=whisper_model),
            'mov': VideoExtractor(use_whisper=use_whisper, model_name=whisper_model),
            'mkv': VideoExtractor(use_whisper=use_whisper, model_name=whisper_model),
            'avi': VideoExtractor(use_whisper=use_whisper, model_name=whisper_model),
            'wmv': VideoExtractor(use_whisper=use_whisper, model_name=whisper_model),
            'webm': VideoExtractor(use_whisper=use_whisper, model_name=whisper_model),
            'mov': VideoExtractor(use_whisper=use_whisper, model_name=whisper_model),
            '3gp': VideoExtractor(use_whisper=use_whisper, model_name=whisper_model),
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
        extractor = self.extractors.get(file_ext)
        if not extractor:
            raise ExtractorNotFound(
                f"Формат файла '.{file_ext}' не поддерживается"
            )

        return extractor


def parse(
    file_path: str,
    original_filename: str = None,
    use_whisper: bool = True,
    whisper_model: str = "base"
) -> Dict[str, Any]:
    """
    Функция обёртка для парсинга файла с использованием UniversalParser
    
    Args:
        file_path: Путь к файлу
        original_filename: Оригинальное имя файла
        use_whisper: Использовать Whisper для аудио/видео
        whisper_model: Модель Whisper (tiny, base, small, medium, large)
    
    Returns:
        Dict с ключами 'text' и 'metadata'
    """
    parser = UniversalParser(use_whisper=use_whisper, whisper_model=whisper_model)
    return parser.parse(file_path, original_filename)
