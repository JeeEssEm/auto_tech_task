class ExtractorNotFound(Exception):
    """Исключение, выбрасываемое cuando формат файла не поддерживается"""
    pass


class ParserConfigError(Exception):
    """Ошибка конфигурации парсера"""
    pass


class TranscriptionError(Exception):
    """Ошибка при транскрипции аудио/видео"""
    pass
