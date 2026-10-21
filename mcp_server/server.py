"""Model Context Protocol server exposing the assistant's tools to Claude Desktop.

Run (stdio):  python mcp_server/server.py
Logging goes to stderr: stdout is reserved for the MCP protocol stream.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
logging.basicConfig(stream=sys.stderr, level=logging.WARNING)

try:  # mcp >= 2.0 renamed FastMCP to MCPServer; the decorator API is the same
    from mcp.server.mcpserver import MCPServer as FastMCP  # noqa: E402
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP  # noqa: E402

from finance_assistant.utils.portfolio import analyze_portfolio  # noqa: E402
from finance_assistant.utils.projections import plan_goal  # noqa: E402
from finance_assistant.utils.trends import trend_metrics  # noqa: E402
from finance_assistant.workflow import FinanceWorkflow  # noqa: E402

mcp = FastMCP("ai-finance-assistant")
_wf: FinanceWorkflow | None = None


def wf() -> FinanceWorkflow:
    global _wf
    if _wf is None:
        _wf = FinanceWorkflow()
    return _wf


@mcp.tool()
def ask_finance_assistant(question: str, thread_id: str = "mcp") -> str:
    """Ask the multi-agent financial-education assistant a question (concepts, taxes, goals, markets)."""
    r = wf().chat(question, thread_id=thread_id)
    return r["response"]


@mcp.tool()
def search_knowledge_base(query: str, k: int = 4) -> str:
    """Semantic search over the curated financial-education knowledge base. Returns passages with titles."""
    hits = wf().retriever.retrieve(query, k=k, include_glossary=True)
    return json.dumps([{"title": h.chunk.title, "category": h.chunk.category, "score": round(h.score, 3),
                        "text": h.chunk.text, "url": h.chunk.url} for h in hits], indent=2)


@mcp.tool()
def get_stock_quote(symbol: str) -> str:
    """Latest quote for a ticker, with a data-freshness label (live, cached, stale, or sample)."""
    return json.dumps(wf().market.get_quote(symbol), indent=2)


@mcp.tool()
def analyze_holdings(holdings_json: str, cash: float = 0.0, risk_profile: str = "moderate") -> str:
    """Analyze a portfolio. holdings_json: '[{"symbol": "VTI", "shares": 10, "cost_basis": 250}]'."""
    holdings = json.loads(holdings_json)
    market = wf().market
    syms = [h["symbol"].upper() for h in holdings]
    prices = {s: q["price"] for s, q in market.get_quotes(syms).items() if "price" in q}
    result = analyze_portfolio(holdings, prices, {s: market.info(s) for s in syms}, cash, risk_profile)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def project_savings_goal(target: float, years: float, saved_so_far: float = 0.0,
                         monthly_contribution: float | None = None, risk_profile: str = "moderate") -> str:
    """Project a savings goal: required monthly amount, projected balance and Monte Carlo success odds."""
    plan = plan_goal(target, years, saved_so_far, monthly_contribution, risk_profile)
    plan.pop("schedule", None)
    if "monte_carlo" in plan:
        plan["monte_carlo"].pop("bands", None)
    return json.dumps(plan, indent=2)


@mcp.tool()
def get_market_overview() -> str:
    """Broad market snapshot (index ETFs as proxies) with freshness labels."""
    return json.dumps(wf().market.market_overview(), indent=2)


@mcp.tool()
def get_price_trend(symbol: str) -> str:
    """Trend metrics for a ticker: 1M/3M return, 50-day average, volatility, drawdown, plus a plain-English reading."""
    hist = wf().market.get_daily(symbol)
    return json.dumps({"symbol": hist["symbol"], "freshness": hist["freshness"],
                       **trend_metrics(hist["series"])}, indent=2)


@mcp.tool()
def get_financial_news(tickers: str = "") -> str:
    """Recent headlines with sentiment. tickers: comma-separated, e.g. 'AAPL,MSFT'; empty for the broad market."""
    syms = [t.strip() for t in tickers.split(",") if t.strip()]
    news = wf().market.get_news(syms)
    return json.dumps({"freshness": news["freshness"], "articles": news["articles"][:8]}, indent=2)


@mcp.resource("glossary://terms")
def glossary() -> str:
    """The full financial glossary as JSON."""
    return json.dumps(wf().retriever.glossary, indent=2)


if __name__ == "__main__":
    mcp.run()
