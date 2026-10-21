# MCP server (Claude Desktop)

`mcp_server/server.py` exposes the assistant over the Model Context Protocol (stdio transport) using the official `mcp` Python SDK. It works with both SDK lines: `mcp` 2.x (`MCPServer`) and 1.x (`FastMCP`).

## Tools
| Tool | Purpose |
|---|---|
| `ask_finance_assistant(question, thread_id)` | Full multi-agent answer |
| `search_knowledge_base(query, k)` | Raw RAG passages with scores |
| `get_stock_quote(symbol)` | Quote with freshness label |
| `analyze_holdings(holdings_json, cash, risk_profile)` | Portfolio analytics JSON |
| `project_savings_goal(target, years, saved_so_far, monthly_contribution, risk_profile)` | Goal projection and Monte Carlo odds |
| `get_market_overview()` | Index-ETF snapshot with freshness labels |
| `get_price_trend(symbol)` | 1M/3M change, moving averages, volatility, drawdown, plain-English reading |
| `get_financial_news(tickers)` | Recent headlines with sentiment (comma-separated tickers, or empty for the market) |

Resource: `glossary://terms`.

## Setup
1. `pip install -r requirements.txt` inside a virtualenv.
2. Test locally: `mcp dev mcp_server/server.py` (opens the MCP Inspector), or run `pytest tests/test_mcp_and_engine.py`, which calls every tool offline.
3. Copy `mcp_server/claude_desktop_config.example.json` into Claude Desktop's config file (Settings → Developer → Edit Config), replacing the absolute paths, then restart Claude Desktop.

Notes: never print to stdout in the server (it carries the protocol); logs go to stderr. API keys go in the `env` block.
