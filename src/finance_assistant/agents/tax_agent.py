from __future__ import annotations

from .base import BaseAgent, summarize_chunks

# Published IRS figures for tax year 2026. Verify at irs.gov before relying on them.
ACCOUNT_FACTS = {
    "401(k)": {"keywords": ["401k", "401(k)", "403b", "workplace"],
               "fact": "2026 employee contribution limit $24,500 (+$8,000 catch-up at 50+)."},
    "IRA": {"keywords": ["ira", "roth", "traditional ira"],
            "fact": "2026 IRA contribution limit $7,500 (+$1,100 catch-up at 50+), shared across traditional and Roth IRAs."},
    "HSA": {"keywords": ["hsa", "health savings"],
            "fact": "2026 HSA limits $4,400 self-only / $8,750 family coverage (+$1,000 catch-up at 55+)."},
}
YEAR_NOTE = "_Contribution limits are for tax year 2026; they change annually, so confirm at irs.gov._"


class TaxEducationAgent(BaseAgent):
    name = "tax_education"
    title = "Tax basics"
    description = "Explains tax concepts and account types (401k, IRA, Roth, HSA, 529, capital gains)."
    role_prompt = ("Explain U.S. tax concepts and account types educationally. Do not give individualized tax "
                   "advice; suggest a tax professional for specific situations.")
    rag_categories = ["taxes", "retirement"]

    def _run(self, state):
        q = state["query"].lower()
        chunks = self.retrieve(state["query"], k=4)
        facts = [f"- **{name}**: {v['fact']}" for name, v in ACCOUNT_FACTS.items() if any(k in q for k in v["keywords"])]
        parts = []
        if chunks:
            parts.append(summarize_chunks(chunks))
        if facts:
            parts.append("**Current limits**\n" + "\n".join(facts) + "\n" + YEAR_NOTE)
        parts.append("For decisions that depend on your full tax picture, a CPA or enrolled agent can help.")
        draft = "\n\n".join(parts)
        content = self.compose(state, draft, chunks)
        sources = self.sources_from(chunks)
        if facts:
            sources.append({"title": "IRS retirement plan limits", "url": "https://www.irs.gov/retirement-plans", "kind": "kb"})
        return self.result(content, sources=sources, confidence=0.8)
