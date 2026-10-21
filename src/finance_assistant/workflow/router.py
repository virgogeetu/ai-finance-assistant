"""Intent router: LLM classification with a deterministic keyword fallback."""
from __future__ import annotations

import re

from ..utils.parsing import extract_tickers

# weighted regex signals per agent
SIGNALS: dict[str, list[tuple[str, float]]] = {
    "portfolio_analysis": [(r"\bmy (portfolio|holdings|investments|allocation)\b", 3), (r"\bportfolio\b", 2),
                           (r"\b(diversif\w*|rebalanc\w*|allocation|concentrat\w*)\b", 1.2),
                           (r"\b\d+\s*(shares?\s+of\s+)?[A-Z]{2,5}\b", 1.5), (r"\breview|analy[sz]e\b", 0.8)],
    "market_analysis": [(r"\b(price|quote|trading at|stock price|how is .* doing|today|market (today|overview|now))\b", 2),
                        (r"\b(up|down) (today|this week)\b", 1.5), (r"\$[A-Z]{1,5}\b", 2),
                        (r"\bmarket\b", 0.8)],
    "goal_planning": [(r"\b(goal|save for|saving for|retire (at|by|early)|down payment|"
                       r"how much (should|do) i (save|need))\b", 2.5),
                      (r"\bin \d+ years\b|\bby 20\d\d\b", 1.5), (r"\b(per|a) month\b|\bmonthly\b", 1),
                      (r"\b(project|projection|plan|millionaire)\b", 1), (r"\bemergency fund\b", 0.8),
                      (r"\bwhat if i (invest|save|saved|put|had|contribute|wait)\b", 1.5)],
    "news_synthesizer": [(r"\b(news|headline|headlines|latest|what happened|why (is|did) .* (up|down|fall|drop|rise))\b", 2.5),
                         (r"\bthis week\b", 0.7)],
    "tax_education": [(r"\b(tax|taxes|taxed|irs|deduct\w*|capital gains?|wash sale|1099)\b", 2.5),
                      (r"\b(roth|ira|401\(?k\)?|hsa|529|rmd)\b", 1.6), (r"\bbracket\b", 1.5)],
    "finance_qa": [(r"\b(what is|what are|what's|explain|how does|how do|difference between|meaning of|define)\b", 1.5)],
}
DESCRIPTIONS = {
    "finance_qa": "general financial education: concepts, definitions, how things work",
    "portfolio_analysis": "review the user's own holdings, allocation, diversification",
    "market_analysis": "current prices/quotes, how a stock or the market is doing",
    "goal_planning": "savings goals, retirement targets, how much to save, projections",
    "news_synthesizer": "recent financial news and why something moved",
    "tax_education": "tax concepts and tax-advantaged accounts (401k, IRA, Roth, HSA, 529)",
}


class Router:
    def __init__(self, llm=None, known_tickers: set[str] | None = None, max_agents: int = 2):
        self.llm, self.known, self.max_agents = llm, known_tickers or set(), max_agents

    def keyword_route(self, query: str, context: dict | None = None) -> tuple[list[str], str]:
        scores = {a: 0.0 for a in SIGNALS}
        for agent, pats in SIGNALS.items():
            for pat, w in pats:
                flags = 0 if pat.startswith(r"\b\d+\s*(shares") or "[A-Z]" in pat else re.I
                if re.search(pat, query, flags):
                    scores[agent] += w
        tickers = extract_tickers(query, self.known)
        if tickers and scores["portfolio_analysis"] < 2:
            scores["market_analysis"] += 1.5
        # follow-ups like "what about its dividend?" stay with the previous specialist
        if context and context.get("last_agents") and re.search(r"^(and |what about|how about|what if)|\b(it|its|that)\b",
                                                               query.lower()):
            for a in context["last_agents"]:
                scores[a] = scores.get(a, 0) + 0.8
        ranked = sorted((s, a) for a, s in scores.items() if s >= 1.5)
        ranked.sort(reverse=True)
        chosen = [a for _, a in ranked[: self.max_agents]]
        # keep the second agent only if it's reasonably strong
        if len(chosen) == 2 and ranked[1][0] < 0.6 * ranked[0][0]:
            chosen = chosen[:1]
        if len(chosen) > 1 and "finance_qa" in chosen:
            chosen.remove("finance_qa")  # specialists already explain concepts
        if not chosen:
            return ["finance_qa"], "default: general education"
        return chosen, "keywords: " + ", ".join(f"{a}={s:.1f}" for s, a in ranked[:3])

    def route(self, query: str, context: dict | None = None) -> tuple[list[str], str]:
        if self.llm is not None and not self.llm.is_mock:
            agents = "\n".join(f"- {k}: {v}" for k, v in DESCRIPTIONS.items())
            out = self.llm.generate_json(
                "You route questions for a financial-education assistant.",
                f"Agents:\n{agents}\n\nPrevious context: {context or {}}\nQuestion: {query}\n\n"
                f'Return {{"agents": [1-{self.max_agents} agent names, most relevant first], "reason": "short"}}')
            if out and isinstance(out.get("agents"), list):
                valid = [a for a in out["agents"] if a in DESCRIPTIONS][: self.max_agents]
                if valid:
                    return valid, "llm: " + str(out.get("reason", ""))[:120]
        return self.keyword_route(query, context)
