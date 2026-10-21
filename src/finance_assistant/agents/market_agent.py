from __future__ import annotations

import re

from ..data.market_data import ProviderError
from ..utils.parsing import extract_tickers
from ..utils.trends import trend_metrics
from .base import BaseAgent


class MarketAnalysisAgent(BaseAgent):
    name = "market_analysis"
    title = "Market snapshot"
    description = "Real-time quotes, price moves and market overview with data-freshness labels."
    role_prompt = ("Describe current market data factually and explain what the metrics mean. Never predict "
                   "prices or say whether to buy. Always mention how fresh the data is.")
    rag_categories = ["stocks", "etfs_funds", "basics"]

    def resolve_tickers(self, state) -> list[str]:
        query = state["query"]
        known = set(self.market.securities)
        tickers = extract_tickers(query, known)
        low = query.lower()
        for sym, meta in self.market.securities.items():  # company names -> tickers
            name = meta.get("name", "").split(" ")[0].lower().strip(",.")
            if len(name) > 3 and re.search(rf"\b{re.escape(name)}\b", low) and sym not in tickers:
                tickers.append(sym)
        if not tickers:
            tickers = extract_tickers(query)  # explicit unknown tickers e.g. $XYZ
        if not tickers and re.search(r"\b(it|its|that stock|this stock|them|those)\b", low):
            tickers = (state.get("context") or {}).get("last_tickers", [])
        return tickers[:6]

    def trends(self, symbols: list[str]) -> dict[str, dict]:
        """Trend context from daily history (one cached call per symbol); skipped quietly if unavailable."""
        out = {}
        for sym in symbols:
            try:
                t = trend_metrics(self.market.get_daily(sym)["series"])
            except ProviderError:
                continue
            if t["points"] >= 2:
                out[sym] = t
        return out

    def _run(self, state):
        tickers = self.resolve_tickers(state)
        overview = not tickers
        quotes = self.market.market_overview() if overview else self.market.get_quotes(tickers)
        rows, fresh = [], set()
        for sym, q in quotes.items():
            if "error" in q:
                rows.append(f"- **{sym}**: data unavailable ({q['error'][:80]})")
                continue
            arrow = "▲" if q["change"] >= 0 else "▼"
            rows.append(f"- **{sym}** ({q.get('name', sym)}): ${q['price']:,.2f} {arrow} "
                        f"{q['change']:+.2f} ({q['change_percent']:+.2f}%) as of {q['latest_trading_day']}")
            fresh.add(q["freshness"]["label"])
        header = "**Market overview** (broad index ETFs as proxies)" if overview else "**Quotes**"
        draft = f"{header}\n" + "\n".join(rows)
        if fresh:
            draft += f"\n\n_Data freshness: {'; '.join(sorted(fresh))}._"
        trends = {} if overview else self.trends([s for s, q in quotes.items() if "error" not in q][:3])
        for sym, t in trends.items():
            draft += f"\n\n**{sym} trend ({t['points']} trading days):**\n" + "\n".join(f"- {line}" for line in t["summary"])
        draft += ("\n\nA daily move is one data point; long-term investors usually focus on diversification "
                  "and time horizon rather than day-to-day changes.")
        chunks = self.retrieve("stock market index daily price change volatility", k=2)
        content = self.compose(state, draft, chunks,
                               "Keep every price and percentage exactly as given, keep the data-freshness note, and explain the "
                               "trend terms (moving average, volatility, drawdown) in one plain sentence each.")
        handoffs = ["news_synthesizer"] if re.search(r"\bwhy\b|news|happen", state["query"].lower()) else []
        return self.result(content, sources=[{"title": f"Market data ({', '.join(sorted(fresh)) or 'n/a'})",
                                              "kind": "market"}] + self.sources_from(chunks),
                           data={"quotes": quotes, "tickers": list(quotes), "overview": overview, "trends": trends},
                           handoffs=handoffs, confidence=0.85)
