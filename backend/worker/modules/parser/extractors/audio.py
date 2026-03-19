"""
Парсер для аудио файлов с использованием Docling и Whisper
"""
from docling.datamodel import asr_model_specs
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import AsrPipelineOptions
from docling.document_converter import AudioFormatOption
from docling.pipeline.asr_pipeline import AsrPipeline

from .base import BaseExtractor


class AudioExtractor(BaseExtractor):
    def __init__(self, use_whisper=True, model_name="base"):
        super().__init__()
        self.use_whisper = use_whisper
        self._converter = None
        match model_name:
            case "tiny":
                self.model_name = asr_model_specs.WHISPER_TINY
            case "base":
                self.model_name = asr_model_specs.WHISPER_BASE
            case "turbo":
                self.model_name = asr_model_specs.WHISPER_TURBO
            case "medium":
                self.model_name = asr_model_specs.WHISPER_MEDIUM
            case _:
                raise Exception("whisper model not found")

    def extract(self, file_path: str, original_filename: str = None):
        if not self.use_whisper:
            raise RuntimeError("Аудио парсер отключен. Включите use_whisper=True")

        metadata = self._get_basic_metadata(original_filename)

        try:
            from docling.document_converter import DocumentConverter
        except ImportError:
            raise ImportError(
                "Docling не установлен. Установите: pip install docling"
            )

        try:

            pipeline_options = AsrPipelineOptions()
            pipeline_options.asr_options = self.model_name

            converter = DocumentConverter(
                format_options={
                    InputFormat.AUDIO: AudioFormatOption(
                        pipeline_cls=AsrPipeline,
                        pipeline_options=pipeline_options,
                    )
                }
            )

            result = converter.convert(file_path)
            text = result.document.export_to_markdown().strip()

            if not text:
                text = "(пустой или не распознаваемый аудиофайл)"

            # Пытаемся получить информацию о длительности
            try:
                import librosa
                y, sr = librosa.load(file_path, sr=None)
                duration = librosa.get_duration(y=y, sr=sr)
                metadata["duration"] = duration
            except Exception:
                pass

            return text, metadata

        except Exception as e:
            raise RuntimeError(
                f"Ошибка при транскрипции аудио (Whisper модель: {self.model_name}): {str(e)}"
            )
