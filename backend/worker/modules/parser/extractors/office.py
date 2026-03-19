from .base import BaseExtractor


class OfficeExtractor(BaseExtractor):
    """
    Парсер для документов Office (DOCX, PPTX, XLSX) и других форматов
    Использует docling для универсального парсинга
    """
    
    def __init__(self):
        super().__init__()
        self._docling = None

    def extract(self, file_path: str, original_filename: str = None):
        metadata = self._get_basic_metadata(original_filename)

        try:
            from docling.document_converter import DocumentConverter
        except ImportError:
            raise ImportError(
                "Docling не установлен. Установите: pip install docling"
            )

        try:
            converter = DocumentConverter()
            result = converter.convert(file_path)
            text = result.document.export_to_markdown()
            
            # Добавляем метаданные если доступны
            if hasattr(result.document, 'pages'):
                metadata["pages"] = len(result.document.pages)

            return text, metadata

        except Exception as e:
            raise ValueError(f"Ошибка чтения документа: {str(e)}")
