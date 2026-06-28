"""Regulation document text extraction helpers."""
from __future__ import annotations

from pathlib import Path


class RegulationDocumentError(ValueError):
    """Raised when a regulation document cannot be converted to text."""


def extract_regulation_text(path: str | Path, original_name: str | None = None) -> str:
    """Extract regulation text from TXT, MD, PDF or DOCX files."""
    file_path = Path(path)
    suffix = (Path(original_name or file_path.name).suffix or file_path.suffix).lower()

    if suffix in {".txt", ".md"}:
        return file_path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".pdf":
        return _extract_pdf_text(file_path)
    if suffix == ".docx":
        return _extract_docx_text(file_path)

    raise RegulationDocumentError(
        f"Unsupported regulation file type '{suffix}'. Upload TXT, MD, PDF or DOCX."
    )


def _extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RegulationDocumentError(
            "PDF regulation upload requires the 'pypdf' package."
        ) from exc

    reader = PdfReader(str(path))
    chunks = [page.extract_text() or "" for page in reader.pages]
    text = "\n\n".join(chunk.strip() for chunk in chunks if chunk.strip())
    if not text:
        raise RegulationDocumentError("No selectable text could be extracted from the PDF.")
    return text


def _extract_docx_text(path: Path) -> str:
    try:
        from docx import Document
    except ImportError as exc:
        raise RegulationDocumentError(
            "DOCX regulation upload requires the 'python-docx' package."
        ) from exc

    document = Document(str(path))
    chunks = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                chunks.append(" | ".join(cells))
    text = "\n\n".join(chunks)
    if not text:
        raise RegulationDocumentError("No text could be extracted from the DOCX document.")
    return text
