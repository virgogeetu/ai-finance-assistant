from __future__ import annotations

from ..utils.parsing import fmt_money, parse_holdings
from ..utils.portfolio import analyze_portfolio
from .base import BaseAgent

CLASS_NAMES = {"us_equity": "U.S. stocks", "intl_equity": "International stocks", "bonds": "Bonds",
               "real_estate": "Real estate", "commodities": "Commodities", "cash": "Cash", "other": "Other"}


class PortfolioAnalysisAgent(BaseAgent):
    name = "portfolio_analysis"
    title = "Portfolio review"
    description = "Reviews a user's holdings: allocation, diversification, concentration, risk."
    role_prompt = ("Explain the user's portfolio analytics in an educational way: what the allocation means, "
                   "where risk is concentrated, and which concepts (diversification, rebalancing) apply. "
                   "Frame suggestions as things to learn about or consider, not orders.")
    rag_categories = ["risk", "investing_strategy", "etfs_funds"]

    def _get_portfolio(self, state) -> dict | None:
        known = set(self.market.securities) if self.market else None
        parsed = parse_holdings(state["query"], known)
        if parsed:
            return {"holdings": parsed, "cash": 0.0}
        p = state.get("portfolio")
        return p if p and p.get("holdings") else None

    def _run(self, state):
        portfolio = self._get_portfolio(state)
        if not portfolio:
            return self.result(
                "To review a portfolio I need your holdings. Add them in the **Portfolio** tab, or type them like "
                "`10 VTI, 25 BND, 5 AAPL`.", confidence=0.5, data={"needs_input": "portfolio"})

        symbols = [h["symbol"].upper() for h in portfolio["holdings"]]
        quotes = self.market.get_quotes(symbols)
        prices = {s: q["price"] for s, q in quotes.items() if "price" in q}
        info = {s: self.market.info(s) for s in symbols}
        risk = portfolio.get("risk_profile") or (state.get("user_profile") or {}).get("risk_profile", "moderate")
        a = analyze_portfolio(portfolio["holdings"], prices, info, float(portfolio.get("cash", 0) or 0), risk)
        if not a["positions"]:  # nothing could be priced (unknown tickers or zero shares)
            names = ", ".join(a["unpriced"]) or "your holdings"
            return self.result(
                f"I couldn't get prices for {names}, so I can't analyze this portfolio yet. "
                "Check the ticker symbols and share counts, then try again.",
                confidence=0.4, data={"needs_input": "portfolio", "unpriced": a["unpriced"]})

        alloc = ", ".join(f"{CLASS_NAMES.get(k, k)} {v:.0%}" for k, v in a["allocation_by_class"].items())
        top = a["positions"][:3]
        lines = [
            f"**Total value:** {fmt_money(a['total_value'])} across {len(a['positions'])} holdings"
            + (f" plus {fmt_money(a['cash'])} cash" if a["cash"] else "") + ".",
            f"**Allocation:** {alloc}.",
            "**Largest positions:** " + ", ".join(f"{p['symbol']} {p['weight']:.0%}" for p in top) + ".",
            f"**Diversification score:** {a['diversification_score']}/100 "
            f"(effective number of holdings ≈ {a['effective_holdings']}).",
            f"**Illustrative long-run assumptions:** expected return ≈ {a['expected_return']:.1%}/yr, "
            f"volatility ≈ {a['expected_volatility']:.1%}/yr. These come from generic asset-class assumptions, not forecasts.",
        ]
        if a.get("unrealized_gain") is not None:
            lines.append(f"**Unrealized gain/loss:** {fmt_money(a['unrealized_gain'])}.")
        if a["flags"]:
            lines.append("**Things worth understanding:**\n" + "\n".join(f"- {f}" for f in a["flags"]))
        drift = {k: v for k, v in a["drift"].items() if abs(v) >= 0.05}
        if drift:
            lines.append(f"**Compared with a simple {risk} reference mix:** " + ", ".join(
                f"{CLASS_NAMES.get(k, k)} {'over' if v > 0 else 'under'} by {abs(v):.0%}" for k, v in drift.items())
                + ". Rebalancing is the process of moving back toward a target.")
            moves = {k: v for k, v in a["rebalance"].items() if k in drift}
            if moves:
                lines.append("**What moving back would look like (illustration only):** " + ", ".join(
                    f"{'add' if v > 0 else 'trim'} about {fmt_money(abs(v))} {CLASS_NAMES.get(k, k)}" for k, v in moves.items())
                    + ". Selling in a taxable account can trigger capital-gains tax, so many people rebalance by "
                      "steering new contributions toward the underweight areas instead.")
        if a.get("return_to_risk") is not None:
            lines.append(f"**Return per unit of risk:** {a['return_to_risk']:.2f} (expected return above cash ÷ volatility, "
                         "a simplified Sharpe ratio; higher means more expected reward for each bump along the way).")
        if a.get("stress_tests"):
            lines.append("**How this mix would have fared in past shocks (rough estimate):** " + "; ".join(
                f"{s['scenario']} {s['change_pct']:+.0%} ({fmt_money(s['change_value'])})" for s in a["stress_tests"])
                + ". Markets recovered from each of these, but it took time.")
        if a["unpriced"]:
            lines.append(f"_Couldn't price: {', '.join(a['unpriced'])}._")
        fresh = next((q["freshness"]["label"] for q in quotes.values() if "freshness" in q), "")
        if fresh:
            lines.append(f"_Prices: {fresh}._")
        draft = "\n\n".join(lines)  # blank lines: Markdown keeps one item per paragraph

        topics = "diversification concentration risk rebalancing asset allocation"
        chunks = self.retrieve(topics + " " + " ".join(f.split(" ")[0] for f in a["flags"]), k=3)
        content = self.compose(state, draft, chunks)
        return self.result(content, sources=self.sources_from(chunks),
                           data={"analysis": a, "tickers": symbols}, confidence=0.9)
