# Changelog

All changes made to this project, newest first.

## 2026-10-20 — Inline tips everywhere (help option 3)

**User experience**
- ⓘ tooltips added to every input, button and number that lacked one: comfort level (fuller explanation), sample picker, Load sample, Start a new conversation, holdings-table columns (Ticker, Shares, Cost per share), Cash, Analyze portfolio, Total value, positions-table Weight and Gain columns, all 7 market-overview tickers (what SPY, QQQ, DIA, IWM, VXUS, BND and GLD represent), Price history, 1-month and 3-month change, and the suggested next-question buttons.
- 💡 "How to read this" lines under every chart: allocation donut, sectors, mix vs. reference, past-shock test, price history, and the Goals projection. Plus a tip under the starter questions, an editing hint under the holdings table, a sentiment note above headlines, and a line in "Sources and routing" explaining what it shows.
- Sample portfolios show friendly names (🌱 Three-fund beginner, 🚀 Tech-heavy, 🏖️ Retiree income, 🏢 Single company stock) and their description before loading.
- The Price history picker shows full fund names ("SPY · SPDR S&P 500 ETF").
- All tip text lives in `ui/help_content.py` (`TIPS`, `OVERVIEW_TIPS`, `SAMPLE_NAMES`).

**Tests**
- `tests/test_ui.py`: a test that every tip key used in `app.py` exists and none are unused (a typo would otherwise crash only when that screen opens), and a test that the tips appear on screen. Suite: 79 passed, coverage 96%, lint clean.
- Checked in the browser (sidebar, sample picker, starter tip) and headlessly for Portfolio, Markets and Goals; the browser pane was too narrow for screenshots of those tabs.

**Documentation**
- `docs/user_guide.md`, `README.md`, `docs/developer_guide.md`, `docs/rubric_map.md`, `docs/testing_checklist.md` (3 new checks; test count 79).

## 2026-10-20 — Soft and friendly style

**Look and feel**
- New theme in `.streamlit/config.toml`: warm cream background, soft mint sidebar, soft green accent, rounded Nunito font at 17px, rounded corners (1rem) with pill-shaped buttons, matching pastel chart colors. Also fixes the old `font = "sans serif"` value, which Streamlit had been ignoring (the valid value is `sans-serif`).
- `ui/app.py`: emoji tab labels (💬 Ask, 📊 Portfolio, 📈 Markets, 🎯 Goals, ❓ Help) kept in constants so tab-switch buttons stay in sync; friendly header ("Hi there 👋 …") and chat prompt ("What would you like to learn today?"); white rounded cards for metrics and chat messages; the freshness note shown as a soft pill; a shared Plotly template so every chart uses the same font and palette.

**Readability fixes found while reviewing every tab**
- Portfolio: holdings and results are now stacked, so charts use the full width instead of 60% of it (labels overlapped before).
- Portfolio, Markets and Goals metrics use a 2×2 grid; on smaller windows the 4-across rows cut values off ("$3…").
- Goals: inputs in a 2×2 grid with tooltips (the +/- buttons were hidden before); new fourth card **Money you put in** with "growth adds $…"; chart lines drawn without stray point markers; legend "Likely range (10th–90th)".
- All charts: small side margins so axis labels are no longer clipped.

**Tests**
- `tests/test_ui.py` updated for the new tab labels. Suite: 77 passed, coverage 96%, lint clean. Checked every tab in the running app (offline mode).

**Documentation**
- `README.md`, `docs/user_guide.md` (Goals cards), `docs/developer_guide.md` (theme file), `docs/rubric_map.md`, `docs/testing_checklist.md` (2 look-and-feel checks).

## 2026-10-20 — Welcome tour and Help tab

**User experience**
- First-visit **welcome tour**: a 3-step dialog (what the app does, where to start, getting help) with Next / Back / Skip, a progress bar, and buttons to open the Help tab or start exploring. Shown once per browser session; reopen with **👋 Tour** in the sidebar or **Replay the welcome tour** in Help. (`ui/app.py`)
- New **Help** tab: quick start, what each tab does, what every number means (12 metrics), a searchable glossary of all 104 terms with **Ask about this in chat** (switches to the Ask tab and answers), and 8 common questions including privacy. Sidebar **📖 Help** button jumps to it. All text lives in the new `ui/help_content.py`.
- Tabs can now be switched by buttons (`st.tabs(..., key="main_tabs", on_change="rerun")`).
- The **Markets tab only fetches prices while it is open**, instead of on every page refresh. This saves Alpha Vantage free-tier calls (25 a day).

**Fixes**
- Offline answers could quote a knowledge-base passage starting mid-sentence (e.g. "the total contributions but more…"), more noticeable since articles were expanded into several passages. The summary now skips a leading fragment. (`agents/base.py`)

**Tests and quality**
- `tests/test_ui.py`: 3 new tests (Markets renders when opened, tour shows on first visit only, glossary search plus "Ask about this in chat"); `tests/test_rag.py`: 1 new test for the fragment fix. Suite: 77 passed, coverage 96%, lint clean.
- `pyproject.toml`: `ui/help_content.py` exempt from the line-length rule (long prose lines).
- Checked in the running app: all three tour steps, Back/Skip, "Open the Help tab", sidebar Help, glossary search and "Ask about this in chat", Markets loading on open.

**Documentation**
- `docs/user_guide.md` (new "Welcome tour and Help" section), `README.md` highlight, `docs/developer_guide.md` code map, `docs/rubric_map.md`, and `docs/testing_checklist.md` (10 new checks; test count 77).

**Not done (by choice)**
- No visual restyle yet: the "Soft and friendly" style and inline tips (help option 3) were left for later.

## 2026-10-19 — Testing checklist

**Documentation**
- New `docs/testing_checklist.md`: a printable, tick-box test pass in five parts (automated tests, the app by hand offline, real API keys, MCP server, content accuracy), with expected results for each step, every 2026 figure to verify against irs.gov, and a results table.
- Linked from `README.md`, `docs/developer_guide.md` and `docs/rubric_map.md`.

## 2026-10-19 — Knowledge base expanded

**Educational content**
- Rewrote the `content` of all 102 articles in `knowledge_base/articles.json` (ids, titles, categories, tags, sources and links unchanged). Articles went from about 60 words on average (minimum 49) to 199–279 words (median 240; about 24,000 words total).
- Each article now gives a plain-language definition, a worked example with numbers, the main trade-offs, and a key takeaway or common mistake. All example figures were checked with a script (loan payments, compound growth, bond prices, yields, tax math, sequence-of-returns example).
- Year-specific figures are labelled 2026 and match `agents/tax_agent.py`: 401(k) $24,500 (+$8,000 at 50+, $11,250 at 60–63), IRA $7,500 (+$1,100), HSA $4,400 / $8,750 (+$1,000 at 55+). Also added, with "confirm at irs.gov": 2026 single-filer brackets, standard deduction ($16,100 / $32,200), SALT cap ($40,400), Roth IRA phase-outs, Child Tax Credit ($2,200), the 2026 non-itemizer charitable deduction, RMD ages 73/75, and the 529 K-12 limit ($20,000 from 2026).
- Small wording tweaks so beginner questions find the right article: "What Is a Stock?" now opens with "A stock is…", and "The 4% Rule" says it answers how long savings last.

**Search quality** (offline hashing embedder, before → after)
- Each article found by its own title in the top 3: 102/102 → 102/102.
- 12 natural beginner questions answered by the right article in the top 3: 8/12 → 10/12. With the real OpenAI index, "when do I have to take money out of my IRA" now finds Required Minimum Distributions; "how long will my savings last" ranks The 4% Rule 4th–5th.
- Index now has 461 passages (was 206). Rebuilt the OpenAI index with `scripts/build_index.py` (small embedding cost).

**Tests**
- Suite: 73 passed, coverage 96%, including the existing retrieval-relevance tests.
- `docs/rubric_map.md` updated to describe the expanded content.

## 2026-10-17 — Rubric improvements

**Fixes**
- MCP server crashed on startup with the installed `mcp` 2.x (`FastMCP` was renamed `MCPServer`). It now works with both 1.x and 2.x. (`mcp_server/server.py`)
- Follow-ups like "What if I invest $450 a month?" went to the general Q&A agent and lost the goal. "What if…" now routes back to the previous specialist and reuses the saved goal. (`workflow/router.py`)
- Offline portfolio and goal answers ran together as one paragraph; each line is now its own paragraph. (`agents/portfolio_agent.py`, `agents/goal_agent.py`)
- Market overview prices were cut off ("$…") on narrow screens; they now show in rows of four. Chart titles and axis labels no longer get clipped. (`ui/app.py`)

**Technical implementation**
- Alpha Vantage requests retry once with backoff on network errors (not on rate limits). (`data/market_data.py`)
- MCP server: 3 new tools, `get_market_overview`, `get_price_trend` and `get_financial_news` (8 in total).

**Market intelligence**
- New `utils/trends.py`: 1M/3M change, 20/50-day moving averages with an uptrend/downtrend/mixed reading, annualized volatility level, max drawdown, each with a plain-English sentence. Used by the market agent (for up to 3 tickers), the Markets tab and MCP.

**Portfolio analysis**
- Stress test: how today's mix would have moved in the 2008 crisis, the 2020 COVID crash and the 2022 rate shock (approximate asset-class returns), in % and dollars.
- Rebalancing amounts in dollars toward the reference mix, with a note on capital-gains tax.
- Return per unit of risk (simplified Sharpe ratio). (`utils/portfolio.py`, `agents/portfolio_agent.py`)

**User experience**
- Suggested next questions as buttons under the latest answer, tailored to what was asked; goal suggestions use the user's own numbers. (`workflow/followups.py`, `ui/app.py`)
- Voice questions: microphone in the chat box when `OPENAI_API_KEY` is set, transcribed with OpenAI (`TRANSCRIBE_MODEL`, default `whisper-1`). (`core/llm.py`, `config.py`)
- New charts: your mix vs. reference mix, past-shock test, 50-day average on the price chart, trend metrics row with explanations, sentiment dots on headlines. Beginner tooltips on portfolio and market metrics.

**Code quality and tests**
- Ruff lint config and coverage config (`fail_under = 90`) in `pyproject.toml`; all lint issues fixed; all Python files normalized to LF line endings.
- 36 new tests in `test_providers.py`, `test_llm.py`, `test_insights.py`, `test_mcp_and_engine.py` and `test_ui.py` (headless Streamlit). Suite: 73 passed, coverage 82% → 96% (`ui/app.py` is covered by the smoke tests, not counted in the percentage).
- Added `pytest-cov` and `ruff` to `requirements.txt` (installed locally).

**Documentation**
- New: `docs/user_guide.md`, `docs/developer_guide.md` (config reference, code map, adding agents and providers, test map), `docs/roadmap.md` (features beyond the brief plus roadmap), `docs/rubric_map.md` (each criterion mapped to code and tests).
- Updated: `docs/architecture.md` (sequence diagram, files and voice, new insights, fallbacks 7–8), `docs/mcp.md` (8 tools, SDK versions), `docs/demo_script.md` (~6 min, covers new features), `README.md` (highlights, docs index, status), `.env.example` (`TRANSCRIBE_MODEL`).

**Verified live** (OpenAI, small cost): a spoken question generated with Windows text-to-speech was transcribed word for word in 1.4 s and answered correctly.

**Not verified**
- Real Alpha Vantage calls for the new trend metrics (avoided to save the 25/day free quota); covered by tests with a fake API.
- The microphone button in a real browser recording (the browser pane can't record audio); the transcription path itself was tested live.

## 2026-10-17 — File attachments in chat

**Features**
- The chat box accepts files (button **+** or drag and drop, several at once, 25 MB each): PDF, Word `.docx`, Excel `.xlsx`, CSV, JSON, `.txt`/`.md`, and images (PNG, JPG, WEBP, GIF). Sending files with no text asks for a plain-language summary. (`ui/app.py`)
- New `src/finance_assistant/core/attachments.py` extracts text from each file, never crashes on bad files (it adds a note instead), and picks the passages most relevant to the question so big files fit in the prompt.
- Images and scanned PDFs are read through the LLM's vision support (`LLMClient.describe_image` in `core/llm.py`). In offline mock mode they show a note saying an LLM provider is needed.
- Files stay with the conversation (`documents` in `core/state.py`, `attachments=` on `FinanceWorkflow.chat`). Every agent uses them when files were attached on that turn or the question refers to them ("my file", "this statement"); unrelated follow-ups ignore them. Uploaded files appear in the answer's sources. (`agents/base.py`, `workflow/graph.py`)
- The Q&A agent also explains glossary terms found in the uploaded file. (`agents/qa_agent.py`)

**Fixes**
- Starter buttons, charts and tables in the UI were squeezed to 1 pixel wide: `width=True` changed to `width="stretch"` (newer Streamlit). (`ui/app.py`)
- Dollar amounts disappeared in chat answers when a message had two of them ("$1,500 … $450" was drawn as a math formula). `$` is now escaped when displaying answers. (`ui/app.py`)
- Glossary lookup now matches terms next to punctuation ("APR:", "ETF,"). (`rag/retriever.py`)

**Dependencies**
- Added `pypdf`, `python-docx`, `openpyxl`, `pillow` to `requirements.txt` (installed locally).

- When two agents answer and one only asks for missing info ("I need your holdings…"), that reply is left out of the final answer. Found in the live test below, where a bank-statement question also went to the portfolio agent. (`workflow/graph.py`)

**Tests**
- New `tests/test_attachments.py` (8 tests: PDF text, scanned PDF, images, Word/Excel/CSV/JSON, bad files, passage selection, end-to-end chat with a file), plus one compose test in `tests/test_workflow.py`. Suite: 37 passed.
- Live check with OpenAI `gpt-4o-mini`: a made-up bank-statement image and the same image saved as a scanned PDF were both transcribed with every number exact (about 2–3 s each). A full chat question about the scan correctly computed the balance change ($1,745.25) and explained APY.

**Other**
- Added `.claude/launch.json` to run the app offline on port 8510 for previews (port 8501 was already in use).
- README: new "Attaching files in chat" section.

## 2026-10-17 — Bug fixes

**Security**
- Added `.dockerignore` so `.env` (API keys) and `.cache/` are no longer copied into the Docker image.

**Fixes**
- Portfolio review no longer crashes when none of the holdings can be priced (unknown ticker or zero shares); it now names the tickers it couldn't price. (`src/finance_assistant/agents/portfolio_agent.py`)
- Goal parsing ignores ages: "I'm 30 years old… in 25 years" now plans for 25 years, not 30. (`src/finance_assistant/utils/parsing.py`)
- Goal parsing treats "to have $X" as the target, not as money already saved. (`src/finance_assistant/utils/parsing.py`)
- A return rate stated in the question ("assuming 8% return") is now used in the projection instead of being ignored. `plan_goal` has a new `annual_return` parameter. (`src/finance_assistant/utils/projections.py`, `src/finance_assistant/agents/goal_agent.py`)

**Configuration**
- `.env`: `MARKET_DATA_PROVIDER` changed from `alphavantage` to `auto`, so yFinance is used when the Alpha Vantage free-tier limit (5/min, 25/day) runs out, instead of mixing live and sample prices.
- Added `.env.example` (all values blank) — the README already referred to it.

**Tests**
- Added 4 tests (age vs. years, stated return rate, "to have" target, unpriceable portfolio). Suite: 29 passed.

**Known, not fixed**
- Tax agent keyword matching finds substrings, e.g. "brother" contains "roth", which can add IRA limits to an answer that already went to the tax agent.
