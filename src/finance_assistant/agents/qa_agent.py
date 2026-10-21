from __future__ import annotations

from .base import BaseAgent, summarize_chunks


class FinanceQAAgent(BaseAgent):
    name = "finance_qa"
    title = "Financial concepts"
    description = "General financial education questions: concepts, definitions, how things work."
    role_prompt = "Answer general financial-education questions using the knowledge base, with examples."

    def _run(self, state):
        query = state["query"]
        if self.uses_files(state):  # also look up terms that appear in the uploaded files
            query += " " + " ".join(d["text"][:400] for d in state["documents"] if d.get("text"))
        chunks = self.retrieve(query, k=4)
        terms = self.retriever.lookup_terms(query) if self.retriever else {}
        parts = []
        if terms:
            parts.append("**Key terms**\n" + "\n".join(f"- **{t}**: {d}" for t, d in list(terms.items())[:4]))
        if chunks:
            parts.append("**From the knowledge base**\n" + summarize_chunks(chunks))
        if not parts:
            parts.append("I couldn't find this topic in my knowledge base yet. Try rephrasing, or ask about "
                         "budgeting, saving, credit, stocks, bonds, ETFs, retirement accounts, or taxes.")
        draft = "\n\n".join(parts)
        content = self.compose(state, draft, chunks)
        top = chunks[0].score if chunks else 0
        sources = self.sources_from(chunks) + [{"title": t, "category": "glossary", "kind": "glossary"} for t in terms]
        return self.result(content, sources=sources, confidence=min(0.95, 0.4 + top),
                           data={"glossary_terms": list(terms)})
