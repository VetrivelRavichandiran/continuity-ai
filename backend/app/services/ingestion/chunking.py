"""Chunking: split extracted text into ~800-char chunks on paragraph
boundaries. Each chunk records document_id, page (1-based or None) and the
character offset within the full text.
"""
from dataclasses import dataclass, field


@dataclass
class ChunkSpec:
    document_id: int
    page: int | None
    char_offset: int
    text: str


def _paragraphs_with_pages(full_text: str, pages: list[str]) -> list[tuple[int | None, str]]:
    """Yield (page_number_1based_or_None, paragraph_text)."""
    if pages:
        for idx, page_text in enumerate(pages, start=1):
            for para in page_text.split("\n"):
                para = para.strip()
                if para:
                    yield (idx, para)
    else:
        for para in full_text.split("\n"):
            para = para.strip()
            if para:
                yield (None, para)


def chunk_text(document_id: int, full_text: str, pages: list[str],
               target: int = 800) -> list[ChunkSpec]:
    chunks: list[ChunkSpec] = []
    current_parts: list[str] = []
    current_len = 0
    current_page: int | None = None
    offset = 0

    def flush() -> None:
        nonlocal current_parts, current_len, current_page, offset
        if current_parts:
            text = "\n".join(current_parts)
            chunks.append(ChunkSpec(
                document_id=document_id,
                page=current_page,
                char_offset=offset,
                text=text,
            ))
            current_parts = []
            current_len = 0
            current_page = None
            offset += len(text) + 1  # +1 for the newline separator

    for page, para in _paragraphs_with_pages(full_text, pages):
        # A single paragraph longer than target: hard-split it.
        while len(para) > target:
            piece = para[:target]
            para = para[target:]
            if current_parts and current_len + len(piece) + 1 > target:
                flush()
            current_parts.append(piece)
            current_len += len(piece) + (1 if len(current_parts) > 1 else 0)
            offset += len(piece)
        if current_page is None:
            current_page = page
        if current_parts and current_len + len(para) + 1 > target:
            flush()
        current_parts.append(para)
        current_len += len(para) + (1 if len(current_parts) > 1 else 0)
        offset += len(para)
    flush()
    return chunks