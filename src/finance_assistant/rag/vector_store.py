"""FAISS vector store (inner product on normalised vectors = cosine).

Falls back to an equivalent NumPy implementation when faiss is not installed,
so the same code runs in CI and on machines without native wheels.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import numpy as np

from .chunker import Chunk

try:
    import faiss  # type: ignore
except ImportError:  # pragma: no cover
    faiss = None


class FaissStore:
    def __init__(self, dim: int):
        self.dim = dim
        self.chunks: list[Chunk] = []
        self._index = faiss.IndexFlatIP(dim) if faiss else None
        self._matrix = np.zeros((0, dim), dtype=np.float32)

    @property
    def backend(self) -> str:
        return "faiss" if self._index is not None else "numpy"

    def add(self, vectors: np.ndarray, chunks: list[Chunk]) -> None:
        vectors = np.ascontiguousarray(vectors, dtype=np.float32)
        if self._index is not None:
            self._index.add(vectors)
        else:
            self._matrix = np.vstack([self._matrix, vectors])
        self.chunks.extend(chunks)

    def search(self, query: np.ndarray, k: int) -> list[tuple[float, Chunk]]:
        if not self.chunks:
            return []
        k = min(k, len(self.chunks))
        q = np.ascontiguousarray(query.reshape(1, -1), dtype=np.float32)
        if self._index is not None:
            scores, idx = self._index.search(q, k)
            pairs = zip(scores[0], idx[0], strict=True)
        else:
            sims = self._matrix @ q[0]
            top = np.argsort(-sims)[:k]
            pairs = ((sims[i], i) for i in top)
        return [(float(s), self.chunks[i]) for s, i in pairs if i >= 0]

    # persistence ---------------------------------------------------------
    def save(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        (path / "chunks.json").write_text(json.dumps([asdict(c) for c in self.chunks]))
        if self._index is not None:
            faiss.write_index(self._index, str(path / "index.faiss"))
        else:
            np.save(path / "vectors.npy", self._matrix)
        (path / "meta.json").write_text(json.dumps({"dim": self.dim, "backend": self.backend}))

    @classmethod
    def load(cls, path: Path) -> "FaissStore | None":
        try:
            meta = json.loads((path / "meta.json").read_text())
            store = cls(meta["dim"])
            if meta["backend"] != store.backend:
                return None  # rebuild if backend changed
            store.chunks = [Chunk(**c) for c in json.loads((path / "chunks.json").read_text())]
            if store._index is not None:
                store._index = faiss.read_index(str(path / "index.faiss"))
            else:
                store._matrix = np.load(path / "vectors.npy")
            return store
        except (FileNotFoundError, KeyError, ValueError):
            return None
