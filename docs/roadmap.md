# Innovation and roadmap

## Beyond the problem statement (implemented)

| Feature | Why it matters for beginners | Where |
|---|---|---|
| **Voice questions** | Ask out loud; transcribed with OpenAI speech-to-text and answered like typed text | `core/llm.py` (`transcribe`), `ui/app.py` |
| **Files in chat** (PDF, scans, images, Word, Excel, CSV) | "Explain my statement" works on the user's own documents; scans and photos are read with LLM vision; only relevant passages go into the prompt | `core/attachments.py` |
| **Past-shock stress test** | Shows how today's mix would have fared in 2008, the 2020 crash and 2022, in dollars, which makes risk concrete | `utils/portfolio.py` (`STRESS_SCENARIOS`) |
| **Rebalancing in dollars** | Turns "you're 39% over in U.S. stocks" into "trim about $19,600", and notes the tax angle | `utils/portfolio.py`, `agents/portfolio_agent.py` |
| **Trend intelligence** | 1M/3M change, 50-day average, volatility and drawdown, each explained in one sentence and labelled as descriptive, not predictive | `utils/trends.py` |
| **Monte Carlo goal planning** | A range of outcomes and a success probability, not one optimistic number | `utils/projections.py` |
| **Suggested next questions** | Beginners often don't know what to ask next; buttons are tailored to the last answer and exercise conversation memory | `workflow/followups.py` |
| **Data-freshness labels** | Every number says whether it is live, cached, stale or sample | `data/market_data.py` |
| **Draft-then-polish generation** | Numbers come from tools, not the LLM, so they can't be invented; works fully offline | `agents/base.py` |
| **MCP server** | The same tools work inside Claude Desktop and other MCP clients | `mcp_server/server.py` |

## Roadmap

### Near term (1–2 months)
1. **Streaming answers.** Use LangGraph `stream_mode="messages"` and `st.write_stream` so long answers appear word by word.
2. **Persistent memory.** Swap `MemorySaver` for `SqliteSaver` (or Postgres) so conversations and attached files survive restarts; add a "my conversations" list.
3. **Spoken answers.** Add a "read aloud" button using a text-to-speech model, completing the voice loop for accessibility.
4. **Holdings from statements.** Detect a holdings table in an uploaded brokerage CSV or PDF and offer to load it into the Portfolio tab.

### Medium term (3–6 months)
5. **Learning paths and quizzes.** Order the 11 knowledge-base categories into short courses with quick quizzes; track progress per user.
6. **Historical backtests.** Use daily history to show how a mix actually performed over 5–10 years (max drawdown, recovery time), complementing the scenario stress test.
7. **Evaluation harness.** A fixed set of questions with expected agents, required facts and forbidden phrases ("you should buy"), scored for every prompt or model change (LLM-as-judge plus rules).
8. **Retrieval upgrades.** Cross-encoder re-ranking and query rewriting for follow-ups; add a source-date field so the tax agent can flag outdated figures automatically.

### Longer term
9. **Accounts aggregation (read-only)** through a provider such as Plaid, with explicit consent, to replace manual holdings entry.
10. **Multilingual support.** Translate questions and answers while keeping the knowledge base in English, starting with Spanish and Hindi.
11. **Mobile app.** A React Native front end calling `FinanceWorkflow.chat()` through a small FastAPI layer; the MCP server already exposes the same tools.

### Technical notes
- The agent contract (`AgentResult`, hand-offs, `max_agents_per_turn`) already supports adding agents without touching the graph. A learning-path agent and a backtest agent would plug in the same way.
- All new numeric features should follow the draft-then-polish rule and come with offline tests, as the current ones do (96% coverage, no network in tests).
