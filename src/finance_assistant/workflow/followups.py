"""Suggested next questions shown as buttons under each answer.

Built from which agents answered and what they found (tickers, goal numbers,
glossary terms), so beginners always have a sensible next step and follow-ups
exercise the conversation memory ("what if I invest $450 a month?").
"""
from __future__ import annotations

GENERIC = {
    "finance_qa": ["Can you explain that with a simple example?", "What mistakes do beginners make with this?"],
    "portfolio_analysis": ["How would rebalancing work for my portfolio?", "What is diversification and why does it matter?",
                           "How does an index fund reduce concentration risk?"],
    "news_synthesizer": ["How should a long-term investor react to headlines?", "What does market sentiment mean?"],
    "tax_education": ["What's the difference between a Roth and a traditional IRA?", "How are capital gains taxed?"],
    "goal_planning": ["Where should I keep money for a short-term goal?", "What is compound interest?"],
    "market_analysis": ["What does volatility mean?", "How does a single stock fit in a diversified portfolio?"],
}


def suggest(results: list[dict], context: dict, query: str, limit: int = 3) -> list[str]:
    out: list[str] = []
    for r in results:
        data = r.get("data") or {}
        agent = r.get("agent")
        if agent == "market_analysis" and not data.get("overview") and data.get("tickers"):
            t = data["tickers"][0]
            out += [f"Any recent news on {t}?", f"What is {t}'s 50-day moving average telling me?"]
        elif agent == "goal_planning" and (plan := data.get("plan")):
            monthly = plan.get("monthly_contribution") or 0
            out += [f"What if I invest ${monthly + 100:,.0f} a month?",
                    f"What if I had {plan['years'] + 5:g} years instead?"]
        elif agent == "finance_qa" and data.get("glossary_terms"):
            term = data["glossary_terms"][0].split(" (")[0]
            out.append(f'Where would I run into "{term if term.isupper() else term.lower()}" in everyday life?')
        out += GENERIC.get(agent, [])
    if context.get("has_files"):
        out.insert(0, "Which financial terms in my file should I understand?")
    seen, final = {query.strip().lower()}, []
    for q in out:
        if q.lower() not in seen:
            seen.add(q.lower())
            final.append(q)
    return final[:limit]
