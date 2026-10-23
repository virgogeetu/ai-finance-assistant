# Rubric map

Where each evaluation criterion is met, with the files and tests that show it.

## Technical implementation (40%)

| Criterion | Evidence |
|---|---|
| **Multi-agent architecture (10)** | Six specialists with distinct tools: `finance_qa` (RAG + glossary), `portfolio_analysis` (analytics, stress tests, rebalancing), `market_analysis` (quotes + trend metrics), `goal_planning` (projections + Monte Carlo), `news_synthesizer` (news + sentiment), `tax_education` (KB + current IRS limits). They communicate only through shared state and a typed `AgentResult` envelope with hand-offs (market → news), a per-turn agent budget, and automatic fallback to `finance_qa` on error. `agents/`, `core/state.py` |
| **LangGraph workflow (10)** | `StateGraph` with a router node, one node per agent, conditional edges that drain a pending queue, and a compose node. Typed state with reducers (`messages`, `documents`), per-thread `MemorySaver` checkpoints, context carried across turns (`last_tickers`, `last_goal`, `last_agents`), "what if…" follow-ups routed back to the previous specialist, and a built-in engine that runs the same nodes without LangGraph. `workflow/graph.py`, `workflow/router.py`; tests `test_workflow.py`, `test_mcp_and_engine.py` |
| **RAG implementation (8)** | 102 articles + 104 glossary terms → sentence-aware chunking with overlap → embeddings (hashing / sentence-transformers / OpenAI / Gemini) → FAISS `IndexFlatIP` (NumPy fallback) → hybrid score (0.75 cosine + 0.25 keyword), threshold, one chunk per article, category filters → numbered inline citations and a sources panel. The index is cached by a fingerprint of the KB. Uploaded files get their own passage selection. `rag/`, `core/attachments.py`; tests `test_rag.py`, `test_attachments.py` |
| **Real-time data (7)** | Alpha Vantage quotes, daily series and news sentiment; yFinance fallback; TTL cache (memory + disk); sliding-window rate limiter matching the free tier; retry with backoff on network errors; stale-cache fallback; labelled sample data; freshness on every number. `data/`; tests `test_providers.py`, `test_market_data.py` |
| **MCP server (5)** | 8 tools (ask, KB search, quote, holdings analysis, goal projection, market overview, price trend, news) plus a `glossary://terms` resource; works with both `mcp` 1.x and 2.x. `mcp_server/`, `docs/mcp.md`; test `test_mcp_and_engine.py` |

## User experience and interface (25%)

| Criterion | Evidence |
|---|---|
| **Web interface (10)** | A "soft and friendly" theme (warm palette, Nunito font, rounded cards, matching chart colors) and five tabs with icons (Ask, Portfolio, Markets, Goals, Help) plus a profile sidebar; ⓘ tooltips on every input, metric and table column plus 💡 chart-reading tips; a first-visit 3-step welcome tour; a Help tab with quick start, metric explanations, a searchable glossary with "Ask about this in chat", and FAQs; starter questions; metric tooltips written for beginners; rows of four so metrics fit narrow screens; file attachments and voice input in the chat box. `ui/app.py`; test `test_ui.py` |
| **Conversational flow (8)** | Per-thread memory; follow-ups reuse context ("what about its dividend?", "what if I invest $500 a month?"); suggested next questions under each answer; uploaded files stay with the conversation; sources and routing shown under every answer. `workflow/followups.py`, `workflow/router.py` |
| **Data visualization (7)** | Portfolio: allocation donut, sector bars, your mix vs. reference mix, past-shock stress chart. Markets: price line with 50-day average, trend metrics, sentiment-tagged headlines. Goals: Monte Carlo fan chart with contributions line and goal marker. |

## Financial domain knowledge (20%)

| Criterion | Evidence |
|---|---|
| **Educational content (8)** | 102 curated articles across 11 categories (about 24,000 words; each 200–280 words with a definition, a worked example with numbers, and a key takeaway or common mistake; year-specific figures labelled 2026) with further-reading links, a 104-term glossary, glossary terms explained inline (also from uploaded files). `knowledge_base/` |
| **Portfolio analysis (7)** | Value, weights, allocation by class and sector, HHI and effective holdings, diversification score, expected return and volatility (correlation-aware), return per unit of risk, concentration and sector flags, drift vs. reference mix, rebalancing amounts in dollars with a tax note, 3 historical stress scenarios, unrealized gains. `utils/portfolio.py` |
| **Market intelligence (5)** | Quotes with freshness, market overview, 1M/3M returns, 50-day and 20-day averages with an uptrend/downtrend/mixed reading, annualized volatility level, max drawdown, news sentiment averages. Every insight is explained in plain words and labelled as descriptive, not a forecast. `utils/trends.py`, `agents/market_agent.py`, `agents/news_agent.py` |

## Code quality and documentation (15%)

| Criterion | Evidence |
|---|---|
| **Security** | Guardrails for public hosting: misuse and prompt-injection filters, personal-data redaction, key scrubbing, per-visitor and site-wide usage limits, file-bomb limits, safe links, hidden error details. `core/guardrails.py`, `docs/security.md`, `tests/test_guardrails.py` |
| **Code organization (5)** | Layered packages (core / agents / rag / data / utils / workflow), pure maths separated from I/O, provider and agent interfaces, typed state, lint-clean with ruff (`pyproject.toml`). |
| **Documentation (5)** | `README.md`, `docs/workflow.svg` (end-to-end workflow diagram, shown in the README), `docs/architecture.md` (data-flow and sequence diagrams), `docs/user_guide.md`, `docs/developer_guide.md` (config reference, adding agents and providers), `docs/mcp.md`, `docs/research.md`, `docs/roadmap.md`, `docs/demo_script.md`, `docs/testing_checklist.md` (printable test pass), `CHANGELOG.md`. |
| **Testing (5)** | 114 offline tests (unit, integration, MCP, headless UI); about 96% line coverage of `src/` and `mcp_server/`, enforced at 90% in `pyproject.toml`; network, LLMs and SDKs replaced by fakes. |

## Innovation (bonus)

Voice questions, file and scan reading with LLM vision, historical stress tests, rebalancing in dollars, trend intelligence, suggested follow-ups, Monte Carlo goals, and a technical roadmap. See `docs/roadmap.md`.
