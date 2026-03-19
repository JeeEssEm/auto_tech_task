"""
Парсер документов, аудио и видео файлов

Использует docling для универсального парсинга и Whisper для транскрипции
"""

from .universal_parser import UniversalParser, parse
from .exceptions import ExtractorNotFound, ParserConfigError, TranscriptionError

__all__ = [
    'UniversalParser',
    'parse',
    'ExtractorNotFound',
    'ParserConfigError',
    'TranscriptionError',
]
