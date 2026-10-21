"""Embedding backends.

`hashing` is a dependency-free, offline embedder (hashed unigrams + bigrams,
sublinear TF, L2-normalised). It is good enough for a 100-article KB and for
tests. Swap in sentence-transformers or a hosted model for better semantics.
"""
from __future__ import annotations

import hashlib
import re

import numpy as np

from ..config import Settings

_TOKEN = re.compile(r"[a-z0-9]+(?:\(k\))?")
STOPWORDS = set("""a an the and or of to in on for is are be it its as at by with from that this
what how why when which who do does i my me you your can should will would about into than then
there their they them we our us vs""".split())


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in STOPWORDS]


class HashingEmbedder:
    def __init__(self, dim: int = 1024):
        self.dim = dim

    def _vec(self, text: str) -> np.ndarray:
        v = np.zeros(self.dim, dtype=np.float32)
        toks = tokenize(text)
        feats = toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:], strict=False)]
        for f in feats:
            h = int(hashlib.md5(f.encode()).hexdigest(), 16)
            v[h % self.dim] += 1.0 if (h >> 64) & 1 else -1.0
        v = np.sign(v) * np.log1p(np.abs(v))
        n = np.linalg.norm(v)
        return v / n if n else v

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return np.vstack([self._vec(t) for t in texts]) if texts else np.zeros((0, self.dim), np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        return self._vec(text)


class _LangChainEmbedder:
    """Adapter for any LangChain `Embeddings` object."""

    def __init__(self, lc):
        self.lc = lc

    @staticmethod
    def _norm(m: np.ndarray) -> np.ndarray:
        n = np.linalg.norm(m, axis=-1, keepdims=True)
        n[n == 0] = 1
        return (m / n).astype(np.float32)

    def embed_documents(self, texts):
        return self._norm(np.array(self.lc.embed_documents(texts)))

    def embed_query(self, text):
        return self._norm(np.array(self.lc.embed_query(text)))


class SentenceTransformerEmbedder:
    def __init__(self, model: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model)

    def embed_documents(self, texts):
        return self.model.encode(texts, normalize_embeddings=True).astype(np.float32)

    def embed_query(self, text):
        return self.model.encode([text], normalize_embeddings=True)[0].astype(np.float32)


def get_embedder(settings: Settings):
    p = settings.embedding_provider
    try:
        if p == "sentence-transformers":
            return SentenceTransformerEmbedder(settings.embedding_model or "all-MiniLM-L6-v2")
        if p == "openai":
            from langchain_openai import OpenAIEmbeddings
            return _LangChainEmbedder(OpenAIEmbeddings(model=settings.embedding_model or "text-embedding-3-small"))
        if p == "gemini":
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            return _LangChainEmbedder(GoogleGenerativeAIEmbeddings(model=settings.embedding_model or "models/text-embedding-004"))
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Embedding provider %s unavailable (%s); using hashing.", p, exc)
    return HashingEmbedder()
