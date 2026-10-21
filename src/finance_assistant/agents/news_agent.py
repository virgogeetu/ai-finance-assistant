from __future__ import annotations

from .base import BaseAgent
from .market_agent import MarketAnalysisAgent


class NewsSynthesizerAgent(BaseAgent):
    name = "news_synthesizer"
    title = "News in context"
    description = "Summarizes recent financial news and explains why it might matter to a long-term investor."
    role_prompt = ("Summarize the headlines neutrally, group related stories, explain unfamiliar terms, and add "
                   "long-term context. Do not speculate beyond the headlines or predict prices.")
    rag_categories = ["basics", "stocks", "bonds", "investing_strategy"]

    def _run(self, state):
        tickers = MarketAnalysisAgent.resolve_tickers(self, state) if self.market else []
        news = self.market.get_news(tickers)
        arts = news["articles"][:6]
        if not arts:
            return self.result("I couldn't find recent news for that right now.", confidence=0.4)
        lines = [f"**Recent headlines{' for ' + ', '.join(tickers) if tickers else ''}:**"]
        for a in arts:
            sent = f" — sentiment: {a['sentiment_label']}" if a["sentiment_label"] != "Not scored" else ""
            lines.append(f"- {a['title']} ({a['source']}){sent}")
        scored = [a["sentiment_score"] for a in arts if a["sentiment_label"] != "Not scored"]
        if scored:
            avg = sum(scored) / len(scored)
            mood = "positive" if avg > 0.15 else "negative" if avg < -0.15 else "mixed/neutral"
            lines.append(f"\nOverall tone of these headlines: **{mood}** (average score {avg:+.2f} on a -1 to +1 scale). "
                         "Headline sentiment is a description of coverage, not a forecast.")
        lines.append(f"_News freshness: {news['freshness']['label']}._")
        draft = "\n".join(lines)
        chunks = self.retrieve(" ".join(a["title"] for a in arts[:3]), k=2)
        content = self.compose(state, draft, chunks)
        sources = [{"title": a["title"], "url": a["url"], "kind": "news"} for a in arts if a["url"]]
        return self.result(content, sources=sources + self.sources_from(chunks),
                           data={"news": arts, "tickers": tickers}, confidence=0.75)
