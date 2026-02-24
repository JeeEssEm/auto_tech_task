"""
Базовый класс для всех парсеров
"""
from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any

class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, file_path: str, original_filename: str = None) -> Tuple[str, Dict[str, Any]]:
        """
        Извлекает текст прямо из файла на диске
        """
        pass

    def _get_basic_metadata(self, original_filename: str = None) -> dict:
        """Минимальные полезные метаданные"""
        return {
            "filename": original_filename or "unknown"
        }
