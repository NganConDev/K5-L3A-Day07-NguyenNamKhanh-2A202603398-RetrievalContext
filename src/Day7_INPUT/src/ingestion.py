"""Read and normalize source data."""
from __future__ import annotations

from pathlib import Path
import re
import unicodedata

from pypdf import PdfReader

from .models import DocumentPage


def load_pdf(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    """Extract each physical page from a PDF and keep its page number and source."""
    if not path.exists():
        raise FileNotFoundError(f"Source file not found: {path}")

    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        pages: list[DocumentPage] = []
        for idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            pages.append(
                DocumentPage(
                    document_id=document_id,
                    source=source,
                    page=idx,
                    text=normalize_text(text),
                    metadata={"source_file": str(path), "page_type": "pdf", "section": infer_section(text)},
                )
            )
        return pages

    text = path.read_text(encoding="utf-8", errors="replace")
    pages = split_text_pages(text, document_id, source, path)
    return pages


def split_text_pages(text: str, document_id: str, source: str, path: Path) -> list[DocumentPage]:
    """Split a text document into page-like units using explicit PAGE markers or fallback chunks."""
    normalized = normalize_text(text)
    pattern = re.compile(r"(?im)^PAGE\s+(\d+)\s*$")
    matches = list(pattern.finditer(normalized))
    sections: list[tuple[int, str]] = []

    if matches:
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(normalized)
            page_number = int(match.group(1))
            sections.append((page_number, normalized[start:end].strip()))
    else:
        raw_pages = re.split(r"(?im)^PAGE\s+\d+\s*$", normalized)
        for index, page_text in enumerate(raw_pages, start=1):
            if page_text.strip():
                sections.append((index, page_text.strip()))

    if not sections:
        sections = [(1, normalized.strip())]

    pages: list[DocumentPage] = []
    for page_number, page_text in sections:
        if page_text.strip():
            pages.append(
                DocumentPage(
                    document_id=document_id,
                    source=source,
                    page=page_number,
                    text=page_text,
                    metadata={"source_file": str(path), "page_type": "text", "section": infer_section(page_text)},
                )
            )
    return pages


def infer_section(text: str) -> str:
    match = re.search(r"(?im)^SECTION:\s*([A-Za-z0-9 _-]+)", text)
    if match:
        return match.group(1).strip().lower().replace(" ", "_")
    return "general"


def normalize_text(text: str) -> str:
    """Normalize Unicode and whitespace without eliminating important structure."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\u00A0", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()
