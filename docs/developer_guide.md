# Developer guide

## Setup

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                     # all values optional
python scripts/build_index.py                            # builds and caches the FAISS index
streamlit run ui/app.py
```

With no keys, everything runs offline: `LLM_PROVIDER=mock` returns tool-computed drafts, embeddings use the hashing embedder, and market data falls back to labelled sample prices.

## Configuration (`.env`)

| Variable | Values | Default | Notes |
|---|---|---|---|
| `LLM_PROVIDER` | `mock`, `openai`, `gemini`, `anthropic` | `mock` | Needs the matching `*_API_KEY` |
| `LLM_MODEL` | model name | provider default | `gpt-4o-mini`, `gemini-2.5-flash`, `claude-sonnet-5-5` |
| `LLM_TEMPERATURE` | float | `0.2` | |
| `TRANSCRIBE_MODEL` | OpenAI speech model | `whisper-1` | Voice input; used whenever `OPENAI_API_KEY` is set |
| `EMBEDDING_PROVIDER` | `hashing`, `sentence-transformers`, `openai`, `gemini` | `hashing` | Index is cached per provider under `.cache/` |
| `EMBEDDING_MODEL` | model name | provider default | |
| `MARKET_DATA_PROVIDER` | `auto`, `alphavantage`, `yfinance`, `sample` | `auto` | `auto` = Alpha Vantage → yFinance → stale cache → sample |
| `ALPHA_VANTAGE_API_KEY` | key | empty | Free tier: 5 calls/min, 25/day |

Code-level settings (chunk size, `top_k`, cache TTLs, rate-limit budgets, `max_agents_per_turn`, `history_window`) live in `src/finance_assistant/config.py`.

## Code map

```
src/finance_assistant/
  config.py                 Settings from the environment
  core/
    llm.py                  LLMClient: text, JSON, image (vision) and speech (transcription), with an offline mock
    state.py                FinanceState (LangGraph state) and the AgentResult envelope
    attachments.py          Read uploaded files into text; pick passages that fit the prompt
  agents/                   BaseAgent + six specialists (qa, portfolio, market, goal, news, tax)
  rag/                      loader → chunker → embeddings → FaissStore → Retriever (hybrid scoring, citations)
  data/                     MarketDataService (provider chain, TTL cache, rate limiter, freshness labels)
  utils/                    Pure maths: portfolio analytics + stress tests, projections + Monte Carlo, trends, parsing
  workflow/                 router.py (LLM + keyword routing), graph.py (LangGraph), followups.py (next questions)
ui/app.py                   Streamlit UI (tabs, welcome tour, Help tab)
ui/help_content.py          Text for the welcome tour, Help tab and inline tips (TIPS, OVERVIEW_TIPS, SAMPLE_NAMES);
                            edit here, not in app.py. A test fails if app.py uses a tip key that doesn't exist.
.streamlit/config.toml      "Soft and friendly" theme: colors, Nunito font, rounded corners, chart colors
mcp_server/server.py        MCP server (8 tools + glossary resource)
```

Design rules:
- **Pure core, thin edges.** Maths in `utils/` has no I/O, so it is easy to test. Network and LLM access sit behind `MarketDataService` and `LLMClient`.
- **Draft, then polish.** Agents compute facts first; the LLM only rewrites the draft and is told not to invent numbers. If the LLM fails, the draft is the answer.
- **Agents never call each other.** They read shared state and return an `AgentResult`; hand-offs go through the orchestrator.

## Adding an agent

1. Create `src/finance_assistant/agents/my_agent.py`:

   ```python
   from .base import BaseAgent

   class InsuranceAgent(BaseAgent):
       name = "insurance_education"
       title = "Insurance basics"
       role_prompt = "Explain insurance concepts in plain language. Never recommend a specific policy."
       rag_categories = ["real_estate_insurance"]

       def _run(self, state):
           chunks = self.retrieve(state["query"], k=3)
           draft = "..."  # facts computed from tools / retrieved text
           return self.result(self.compose(state, draft, chunks), sources=self.sources_from(chunks))
   ```

2. Add the class to `ALL_AGENTS` in `agents/__init__.py`. The graph creates a node for it automatically.
3. In `workflow/router.py`, add keyword `SIGNALS` and a one-line entry in `DESCRIPTIONS` (used by the LLM router).
4. Optionally add follow-up questions in `workflow/followups.py`.
5. Add tests: a routing case in `tests/test_workflow.py` and an end-to-end `workflow.chat(...)` check.

`BaseAgent.run` already provides timing, exception capture (failures fall back to `finance_qa`), uploaded-file context and source attribution.

## Adding a market-data provider

Implement `name`, `quote(symbol)`, `daily(symbol)` and `news(tickers)`, returning the same dict shapes as `AlphaVantageProvider`. Raise `ProviderError` (or `RateLimited`) on failure. Then add it to `MarketDataService._providers()`. Caching, stale fallback and freshness labels apply automatically.

## Testing and quality

```bash
pytest                      # 114 offline tests: unit, integration, MCP, UI smoke tests
pytest --cov                # coverage report; fails under 90% (currently ~96% of src/ and mcp_server/)
ruff check .                # lint (config in pyproject.toml)
python scripts/run_tests_without_pytest.py   # minimal runner if pytest isn't installed
```

No test touches the network or needs an API key. Providers, LLMs, `openai`, `requests` and `yfinance` are replaced by fakes (`tests/test_providers.py`, `tests/test_llm.py`). The Streamlit UI is exercised headlessly with `streamlit.testing.v1.AppTest` (`tests/test_ui.py`); coverage numbers exclude `ui/app.py`, so these smoke tests stand in for it.

| Test file | Covers |
|---|---|
| `test_utils.py` | Projections, Monte Carlo, portfolio maths, text parsing |
| `test_insights.py` | Trend metrics, stress tests, rebalancing, goal agent, follow-up suggestions |
| `test_rag.py` | KB size, chunking, retrieval relevance, category filters, glossary |
| `test_market_data.py`, `test_providers.py` | Cache, rate limiter, Alpha Vantage parsing / throttling / retries, yFinance, fallback chain |
| `test_llm.py` | LLM wrapper, JSON parsing, vision, transcription, LLM routing, embeddings |
| `test_workflow.py` | Routing, end-to-end chat, memory, hand-offs, fallbacks |
| `test_attachments.py` | PDF, scans, images, Word, Excel, CSV, JSON, bad files, chat with files |
| `test_mcp_and_engine.py` | All MCP tools, built-in engine without LangGraph, error paths, NumPy vector store |
| `test_ui.py` | App loads, starter question, follow-ups, portfolio analysis |

For a full manual test pass (UI, live keys, MCP and fact-checking), use [testing_checklist.md](testing_checklist.md).

## Running in a preview without spending API credits

`.claude/launch.json` starts Streamlit on port 8510 with `LLM_PROVIDER=mock`, `EMBEDDING_PROVIDER=hashing` and `MARKET_DATA_PROVIDER=sample`, which override `.env`.

## Deployment

```bash
docker build -t ai-finance-assistant .
docker run -p 8501:8501 --env-file .env ai-finance-assistant
```

`.dockerignore` keeps `.env` and `.cache/` out of the image; pass keys at run time with `--env-file`. On Streamlit Community Cloud, point the app at `ui/app.py` and add keys as secrets.
