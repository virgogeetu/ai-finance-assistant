from finance_assistant.rag.chunker import chunk_document
from finance_assistant.rag.loader import Document, load_articles, load_glossary
from finance_assistant.rag.retriever import Retriever


def test_knowledge_base_size(settings):
    arts = load_articles(settings.kb_dir)
    assert len(arts) >= 100
    assert len({a.category for a in arts}) >= 10
    assert len(load_glossary(settings.kb_dir)) >= 100


def test_chunking_respects_size_and_overlap():
    text = " ".join(f"Sentence number {i} talks about saving money." for i in range(40))
    chunks = chunk_document(Document("d", "T", "basics", text), size=200, overlap=40)
    assert len(chunks) > 3
    assert all(len(c.text) <= 200 + 60 for c in chunks)


def test_retrieval_relevance_and_attribution(settings):
    r = Retriever(settings)
    cases = {"what is an expense ratio on a fund": "Expense Ratios",
             "how do bond prices react when interest rates rise": "Bond Prices and Interest Rates",
             "difference between roth and traditional ira": "Traditional vs. Roth IRAs",
             "how should I pay off credit card debt avalanche or snowball": "Debt Avalanche vs. Debt Snowball"}
    for q, title in cases.items():
        hits = r.retrieve(q, k=3, include_glossary=False)
        assert title in [h.chunk.title for h in hits], (q, [h.chunk.title for h in hits])
        assert all(0 <= h.score <= 1 for h in hits)
        cite = hits[0].citation()
        assert cite["title"] and cite["category"] and "score" in cite


def test_category_filter(settings):
    r = Retriever(settings)
    hits = r.retrieve("tax on selling stock", k=4, categories=["taxes"], include_glossary=False)
    assert hits and all(h.chunk.category == "taxes" for h in hits)


def test_glossary_lookup(settings):
    r = Retriever(settings)
    terms = r.lookup_terms("What's a good APR and how does an ETF work?")
    assert "Annual Percentage Rate (APR)" in terms and "Exchange-Traded Fund (ETF)" in terms


def test_offline_summary_skips_mid_sentence_overlap():
    from finance_assistant.agents.base import summarize_chunks
    from finance_assistant.rag.chunker import Chunk
    from finance_assistant.rag.retriever import RetrievedChunk
    chunk = Chunk(id="d#1", doc_id="d", title="Compounding", category="basics",
                  text="Compounding. the total contributions but more. Starting early matters most. Debt compounds too.")
    out = summarize_chunks([RetrievedChunk(chunk, 0.5, 0.5, 0.5)])
    assert "Starting early matters most. Debt compounds too." in out and "the total contributions" not in out
