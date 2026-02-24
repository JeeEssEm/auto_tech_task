import chardet
import re
from .base import BaseExtractor

class TextExtractor(BaseExtractor):
    def extract(self, file_path: str, original_filename: str = None):
        metadata = self._get_basic_metadata(original_filename)

        # Определяем кодировку по первым 10КБ
        with open(file_path, 'rb') as f:
            raw_data = f.read(10000)
            encoding = 'utf-8'
            if raw_data:
                result = chardet.detect(raw_data)
                if result['confidence'] and result['confidence'] > 0.7:
                    encoding = result['encoding'] or 'utf-8'

        # Читаем текст из файла с нужной кодировкой
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                text = f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()

        if original_filename and original_filename.lower().endswith('.md'):
            text = self._clean_markdown(text)

        return text, metadata

    def _clean_markdown(self, text: str) -> str:
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        return text.strip()
