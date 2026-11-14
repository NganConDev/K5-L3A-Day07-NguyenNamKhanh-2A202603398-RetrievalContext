"""Implement fixed-size and structure-aware chunking."""
from __future__ import annotations

import re

from .models import Chunk, DocumentPage


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    """Split text into overlapping windows and retain page metadata."""
    if size <= 0:
        raise ValueError("size must be positive")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be between 0 and size")

    text = page.text.strip()
    if not text:
        return []

    words = re.split(r"\s+", text)
    chunks: list[Chunk] = []
    step = size - overlap
    start = 0
    index = 0
    while start < len(words):
        end = min(len(words), start + size)
        window = " ".join(words[start:end])
        if window.strip():
            chunks.append(
                Chunk(
                    chunk_id=f"{page.document_id}-p{page.page}-{index}",
                    document_id=page.document_id,
                    source=page.source,
                    page=page.page,
                    text=window.strip(),
                    metadata={**page.metadata, "strategy": "fixed_size", "chunk_index": index},
                )
            )
            index += 1
        if end == len(words):
            break
        start += step
    return chunks


def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    """Group paragraphs, split oversized paragraphs and retain metadata."""
    if max_size <= 0:
        raise ValueError("max_size must be positive")

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", page.text.strip()) if p.strip()]
    chunks: list[Chunk] = []
    current: list[str] = []
    current_len = 0
    chunk_index = 0

    for paragraph in paragraphs:
        words = paragraph.split()
        if len(words) <= max_size:
            if current_len + len(words) <= max_size:
                current.append(paragraph)
                current_len += len(words)
            else:
                if current:
                    chunks.append(build_chunk(page, chunk_index, " ".join(current)))
                    chunk_index += 1
                current = [paragraph]
                current_len = len(words)
        else:
            if current:
                chunks.append(build_chunk(page, chunk_index, " ".join(current)))
                chunk_index += 1
                current = []
                current_len = 0
            for i in range(0, len(words), max_size):
                segment = " ".join(words[i : i + max_size])
                chunks.append(build_chunk(page, chunk_index, segment))
                chunk_index += 1

    if current:
        chunks.append(build_chunk(page, chunk_index, " ".join(current)))

    return chunks


def build_chunk(page: DocumentPage, index: int, text: str) -> Chunk:
    return Chunk(
        chunk_id=f"{page.document_id}-p{page.page}-{index}",
        document_id=page.document_id,
        source=page.source,
        page=page.page,
        text=text.strip(),
        metadata={**page.metadata, "strategy": "by_paragraph", "chunk_index": index},
    )
