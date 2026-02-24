"""
Модуль парсеров для разных форматов
"""

from .base import BaseExtractor
from .text import TextExtractor
from .json import JsonExtractor
from .office import OfficeExtractor
from .audio import AudioExtractor
from .video import VideoExtractor

__all__ = [
    'BaseExtractor',
    'TextExtractor',
    'JsonExtractor',
    'OfficeExtractor',
    'AudioExtractor',
    'VideoExtractor',
]