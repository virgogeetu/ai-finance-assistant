# AI Finance Assistant
*Democratizing Financial Literacy Through Intelligent Conversational AI*

A multi-agent financial-education assistant: six specialised agents orchestrated with LangGraph, retrieval over a curated knowledge base in FAISS, live market data from Alpha Vantage (with yFinance and offline fallbacks), a Streamlit interface with file and voice input, and an MCP server for Claude Desktop.

> Educational tool only. It does not provide personalised investment, tax or legal advice.

## Highlights

- **Six agents, one conversation.** Concepts, portfolio review, market snapshot, goal planning, news and taxes, routed by an LLM (with a keyword fallback) and able to hand off to each other ("Why is NVDA down?" → market + news).
- **Remembers the conversation.** "What if I invest $500 a month?" reuses your goal; "any news on it?" knows the stock; suggested next questions under every answer.
- **Grounded answers.** Numbers come from tools, never the LLM; knowledge-base answers cite numbered sources; every price shows how fresh it is.
- **Portfolio insight.** Diversification score, correlation-aware volatility, concentration flags, mix vs. a reference mix, rebalancing amounts in dollars, and a stress test against 2008, 2020 and 2022.
- **Market intelligence.** 1- and 3-month change, 50-day average, volatility, drawdown and news sentiment, each explained in one plain sentence.
- **Your files and your voice.** Attach PDFs, scans, photos, Word, Excel or CSV and ask about them; ask questions out loud.
- **Soft, friendly design.** Warm colors, rounded cards, a larger rounded font, emoji tab icons, and layouts that keep every number readable on smaller screens.
- **Built-in help for beginners.** ⓘ tooltips on every input and number, 💡 "how to read this" lines under every chart, a first-visit welcome tour, a Help tab with a searchable 104-term glossary, explanations of every number, and FAQs.
- **Runs anywhere.** Fully offline with no keys (sample data, tool-computed drafts); OpenAI, Gemini or Claude when configured.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # optional: add an LLM key and ALPHA_VANTAGE_API_KEY
python scripts/build_index.py   # builds the FAISS index
streamlit run ui/app.py
```

Runs fully offline with defaults (`LLM_PROVIDER=mock`, sample market data). Set `LLM_PROVIDER=gemini|openai|anthropic` plus the matching key for generated explanations and for reading images, `OPENAI_API_KEY` for voice input, and `ALPHA_VANTAGE_API_KEY` for real quotes.

Other entry points: `python scripts/cli.py` (terminal chat), `python mcp_server/server.py` (MCP), `pytest --cov` (tests and coverage), `ruff check .` (lint).

## Documentation

| Guide | For |
|---|---|
| [docs/user_guide.md](docs/user_guide.md) | Using every tab, files, voice, what each metric means |
| [docs/architecture.md](docs/architecture.md) | Data flow and sequence diagrams, agents, state, fallbacks, RAG, market data |
| [docs/developer_guide.md](docs/developer_guide.md) | Setup, configuration reference, code map, adding agents and providers, testing |
| [docs/mcp.md](docs/mcp.md) | MCP tools and Claude Desktop setup |
| [docs/research.md](docs/research.md) | Platform and framework research, design decisions |
| [docs/roadmap.md](docs/roadmap.md) | Features beyond the brief and the technical roadmap |
| [docs/rubric_map.md](docs/rubric_map.md) | Each evaluation criterion mapped to code and tests |
| [docs/testing_checklist.md](docs/testing_checklist.md) | Step-by-step test pass: automated, manual UI, live keys, MCP, content accuracy |
| [docs/deployment.md](docs/deployment.md) | Hosting on Streamlit Community Cloud or Docker |
| [docs/security.md](docs/security.md) | Guardrails: misuse, prompt injection, personal data, keys, usage limits, files |
| [docs/demo_script.md](docs/demo_script.md) | Demo video script |
| [CHANGELOG.md](CHANGELOG.md) | Every change, newest first |

## Project structure

```
knowledge_base/      articles.json (102), glossary.json (104), securities.json, sample_portfolios.json
src/finance_assistant/
  config.py          settings from env
  core/              llm.py (provider wrapper, vision, transcription, mock), state.py (state + AgentResult),
                     attachments.py (read uploaded PDFs, images, Word, Excel, CSV, text)
  agents/            base.py + qa, portfolio, market, goal, news, tax agents
  rag/               loader, chunker, embeddings, vector_store (FAISS), retriever
  data/              market_data.py (Alpha Vantage / yFinance / sample), cache.py, rate_limiter.py
  utils/             portfolio.py (analytics, stress tests), projections.py (goals, Monte Carlo),
                     trends.py (moving averages, volatility, drawdown), parsing.py
  workflow/          router.py, graph.py (LangGraph orchestration + memory + fallbacks), followups.py
ui/app.py            Streamlit: Ask · Portfolio · Markets · Goals
mcp_server/          MCP server (8 tools + glossary resource) + Claude Desktop config example
tests/               79 offline tests: unit, integration, MCP, headless UI (~96% coverage)
docs/                guides listed above
```

## Status

| Phase | Item | Where |
|---|---|---|
| Research & design | Platforms, frameworks, architecture, protocol | `docs/research.md`, `docs/architecture.md` |
| 1. Knowledge base | 102 articles in 11 categories, 104-term glossary, sample portfolios | `knowledge_base/` |
| 2. Core agents | Base class, Q&A + RAG, Portfolio, Market | `agents/` |
| 3. Advanced agents | Goal planning (projections + Monte Carlo), News, Tax; hand-offs | `agents/`, `workflow/graph.py` |
| 4. Orchestration | LangGraph routing, state, fallbacks, per-thread memory, follow-up suggestions | `workflow/` |
| 6. RAG | FAISS, chunking, embeddings, hybrid relevance scoring, attribution | `rag/` |
| 7. UI | Chat with files and voice, portfolio dashboard with stress test, market trends, goal planner | `ui/app.py` |
| 8. Real-time data | Alpha Vantage, caching, rate limits, retries, stale fallback, freshness labels | `data/` |
| 9. Testing | 79 offline tests, ~96% coverage (90% enforced), lint-clean | `tests/`, `pyproject.toml` |
| 10. Docs & deploy | Guides, rubric map, roadmap, demo script, Dockerfile | `docs/`, `Dockerfile` |
| 11. MCP (stretch) | 8 tools + glossary resource; `mcp` 1.x and 2.x | `mcp_server/` |

Remaining human tasks: record the demo video (`docs/demo_script.md`) and user acceptance testing.

## Attaching files and voice

Click **+** in the chat box (or drag files in) to attach files up to 25 MB each: PDF, Word (`.docx`), Excel (`.xlsx`), CSV, JSON, text/Markdown, and images (PNG, JPG, WEBP, GIF). Send a file with no text to get a plain-language summary. Files stay with the conversation until you click **Start a new conversation**. When `OPENAI_API_KEY` is set, a microphone appears for spoken questions.

- Text is extracted locally (`src/finance_assistant/core/attachments.py`); only the passages most relevant to your question go to the LLM.
- Images and scanned PDFs are read by the configured LLM's vision support, so they need `LLM_PROVIDER` set (not `mock`).
- With a real LLM configured, file contents and recordings are sent to that provider, so avoid uploading account numbers or other sensitive details.

## Configuration

See `.env.example` and the configuration table in [docs/developer_guide.md](docs/developer_guide.md). Key settings in `config.py`: chunk size/overlap, `top_k`, `min_relevance`, cache TTLs, Alpha Vantage budgets (5/min, 25/day on the free tier), `max_agents_per_turn`.

## Deployment

```bash
docker build -t ai-finance-assistant .
docker run -p 8501:8501 --env-file .env ai-finance-assistant
```
`.dockerignore` keeps `.env` out of the image. Streamlit Community Cloud also works: point it at `ui/app.py` and add keys as secrets.
