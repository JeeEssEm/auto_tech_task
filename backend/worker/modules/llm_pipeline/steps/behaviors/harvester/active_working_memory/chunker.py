# chunker.py
from dataclasses import dataclass
from langchain_text_splitters import RecursiveCharacterTextSplitter

CHUNK_SIZE = 5000        # токены ≈ символы * 0.4, берём с запасом
CHUNK_OVERLAP = 300

SEPARATORS = ["\n## ", "\n# ", "\n\n", "\n", " "]


@dataclass
class Chunk:
    index: int
    text: str
    source_context: str = ""  # заполняется после первого чанка


def chunk_document(text: str, source_meta: str) -> list[Chunk]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=SEPARATORS,
    )
    parts = splitter.split_text(text)
    chunks = [Chunk(index=i, text=part) for i, part in enumerate(parts)]

    # source_meta инжектируется в каждый чанк как метаданные
    # LLM видит их в промпте, не в тексте чанка
    for c in chunks:
        c.source_context = source_meta

    return chunks
