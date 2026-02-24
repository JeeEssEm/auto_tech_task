import docx

from .base import BaseExtractor

class OfficeExtractor(BaseExtractor):
    def extract(self, file_path: str, original_filename: str = None):
        metadata = self._get_basic_metadata(original_filename)

        try:
            doc = docx.Document(file_path)
        except Exception as e:
            raise ValueError(f"Ошибка чтения DOCX файла: {str(e)}")

        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        text = '\n'.join(paragraphs)

        try:
            core_props = doc.core_properties
            if core_props.created:
                metadata["created_time"] = str(core_props.created)
        except:
            pass

        return text, metadata
