"""Sentence-aware chunking with character overlap."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .loader import Document

_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")


@dataclass
class Chunk:
    id: str
    doc_id: str
    title: str
    category: str
    text: str
    url: str = ""
    kind: str = "kb"
    tags: list[str] = field(default_factory=list)


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT.split(text.strip()) if s.strip()]


def chunk_document(doc: Document, size: int = 600, overlap: int = 100) -> list[Chunk]:
    sentences = split_sentences(doc.text)
    chunks, buf = [], ""
    for sent in sentences:
        if buf and len(buf) + len(sent) + 1 > size:
            chunks.append(buf)
            tail = buf[-overlap:] if overlap else ""
            # start the overlap on a word boundary
            buf = (tail[tail.find(" ") + 1:] + " " + sent).strip() if tail else sent
        else:
            buf = f"{buf} {sent}".strip()
    if buf:
        chunks.append(buf)
    return [Chunk(id=f"{doc.id}#{i}", doc_id=doc.id, title=doc.title, category=doc.category,
                  text=f"{doc.title}. {c}" if doc.kind == "kb" else c, url=doc.url, kind=doc.kind, tags=doc.tags)
            for i, c in enumerate(chunks)]


def chunk_documents(docs: list[Document], size: int = 600, overlap: int = 100) -> list[Chunk]:
    return [c for d in docs for c in chunk_document(d, size, overlap)]
