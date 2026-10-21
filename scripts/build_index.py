"""Pre-build the vector index:  python scripts/build_index.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from finance_assistant.config import get_settings  # noqa: E402
from finance_assistant.rag.retriever import Retriever  # noqa: E402

r = Retriever(get_settings())
print(f"Index ready: {len(r.store.chunks)} chunks, backend={r.store.backend}, embedder={type(r.embedder).__name__}")
for q in ["what is an expense ratio", "roth vs traditional", "how do bonds react to rising rates"]:
    print(f"\n> {q}")
    for h in r.retrieve(q, k=3):
        print(f"  {h.score:.3f}  {h.chunk.title} ({h.chunk.category})")
