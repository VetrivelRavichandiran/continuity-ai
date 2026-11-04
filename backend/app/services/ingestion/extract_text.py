"""Text extraction for PDF / DOCX / TXT / MD.

Returns (full_text, pages) where pages is a list of per-page strings (page
boundaries where the format provides them) or [] for flat text formats.
"""
import io

import pymupdf
from docx import Document as DocxDocument


class ExtractionError(Exception):
    pass


def extract_pdf(data: bytes) -> tuple[str, list[str]]:
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        raise ExtractionError(f"Malformed PDF: {exc}") from exc
    pages: list[str] = []
    with doc:
        for page in doc:
            try:
                pages.append(page.get_text("text") or "")
            except Exception:  # noqa: BLE001
                pages.append("")
    full = "\n\n".join(p for p in pages if p.strip())
    if not full.strip():
        raise ExtractionError("no extractable text")
    return full, pages


def extract_docx(data: bytes) -> tuple[str, list[str]]:
    try:
        doc = DocxDocument(io.BytesIO(data))
    except Exception as exc:  # noqa: BLE001
        raise ExtractionError(f"Malformed DOCX: {exc}") from exc
    paragraphs = [p.text for p in doc.paragraphs]
    # Include table cells (team tables, milestone tables) as text lines.
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            paragraphs.append(" | ".join(cells))
    text = "\n".join(paragraphs)
    if not text.strip():
        raise ExtractionError("no extractable text")
    return text, []  # no reliable page boundaries for docx


def extract_plain(data: bytes) -> tuple[str, list[str]]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("utf-8", errors="replace")
    if not text.strip():
        raise ExtractionError("no extractable text")
    return text, []


def extract_text(file_type: str, data: bytes) -> tuple[str, list[str]]:
    ft = (file_type or "").lower().lstrip(".")
    if ft == "pdf":
        return extract_pdf(data)
    if ft == "docx":
        return extract_docx(data)
    if ft in ("txt", "md", "markdown"):
        return extract_plain(data)
    raise ExtractionError(f"Unsupported file type: {ft}")