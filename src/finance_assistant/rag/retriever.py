"""Retrieval pipeline: dense search + keyword re-scoring + attribution."""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass

from ..config import Settings
from .chunker import Chunk, chunk_documents
from .embeddings import get_embedder, tokenize
from .loader import load_all, load_glossary
from .vector_store import FaissStore

log = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float        # hybrid relevance in [0, 1]
    dense: float
    keyword: float

    def citation(self) -> dict:
        return {"title": self.chunk.title, "category": self.chunk.category, "url": self.chunk.url,
                "score": round(self.score, 3), "kind": self.chunk.kind}


class Retriever:
    DENSE_WEIGHT = 0.75

    def __init__(self, settings: Settings):
        self.settings = settings
        self.embedder = get_embedder(settings)
        self.glossary = load_glossary(settings.kb_dir)
        self.store = self._load_or_build()

    def _kb_fingerprint(self) -> str:
        h = hashlib.sha1()
        for name in ("articles.json", "glossary.json"):
            h.update((self.settings.kb_dir / name).read_bytes())
        h.update(f"{self.settings.chunk_size}-{self.settings.chunk_overlap}".encode())
        return h.hexdigest()[:12]

    def _load_or_build(self) -> FaissStore:
        path = self.settings.index_dir / self._kb_fingerprint()
        store = FaissStore.load(path)
        if store is not None:
            return store
        return self.build(path)

    def build(self, path=None) -> FaissStore:
        docs = load_all(self.settings.kb_dir)
        chunks = chunk_documents(docs, self.settings.chunk_size, self.settings.chunk_overlap)
        vectors = self.embedder.embed_documents([c.text for c in chunks])
        store = FaissStore(vectors.shape[1])
        store.add(vectors, chunks)
        if path is not None:
            try:
                store.save(path)
            except OSError as exc:
                log.warning("Could not persist index: %s", exc)
        log.info("Built %s index with %d chunks", store.backend, len(chunks))
        return store

    @staticmethod
    def _keyword_score(query: str, chunk: Chunk) -> float:
        q = set(tokenize(query))
        if not q:
            return 0.0
        title = set(tokenize(chunk.title)) | {t for tag in chunk.tags for t in tokenize(tag)}
        body = set(tokenize(chunk.text))
        return min(1.0, (len(q & title) * 1.5 + len(q & body) * 0.5) / len(q))

    def retrieve(self, query: str, k: int | None = None, categories: list[str] | None = None,
                 include_glossary: bool = True) -> list[RetrievedChunk]:
        k = k or self.settings.top_k
        hits = self.store.search(self.embedder.embed_query(query), k * 6)
        results, seen = [], set()
        for dense, chunk in hits:
            if categories and chunk.category not in categories and chunk.kind != "glossary":
                continue
            if not include_glossary and chunk.kind == "glossary":
                continue
            if chunk.doc_id in seen:
                continue
            kw = self._keyword_score(query, chunk)
            score = self.DENSE_WEIGHT * max(dense, 0) + (1 - self.DENSE_WEIGHT) * kw
            if score < self.settings.min_relevance:
                continue
            seen.add(chunk.doc_id)
            results.append(RetrievedChunk(chunk, score, dense, kw))
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:k]

    def lookup_terms(self, text: str) -> dict[str, str]:
        """Glossary terms mentioned in text (matches full term or parenthetical abbreviation)."""
        low = " " + re.sub(r"[:;,.!\"]", " ", text.lower()) + " "  # "APR:" / "ETF," still match
        found = {}
        for term, definition in self.glossary.items():
            base = term.split(" (")[0].lower()
            abbr = term[term.find("(") + 1:term.find(")")].lower() if "(" in term else None
            if f" {base} " in low or f" {base}?" in low or f" {base}s " in low or (
                    abbr and len(abbr) > 1 and f" {abbr} " in low.replace("?", " ")):
                found[term] = definition
        return found
