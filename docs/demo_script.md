# Demo video script (~6 minutes)

Run with a real LLM key for polished answers, or offline (`LLM_PROVIDER=mock`) to show the tool-computed drafts.

1. **Intro (20s).** The problem: generic articles don't look at your situation, and robo-advisors don't explain. Show the four tabs and the profile sidebar.
2. **Concept Q&A with sources (40s).** Ask "What's the difference between an ETF and a mutual fund?" Open *Sources and routing* to show `finance_qa`, numbered citations, glossary terms and article links. Click a suggested next question.
3. **Portfolio (70s).** Load the `tech_heavy` sample, then **Analyze portfolio**. Walk through the metrics (hover the tooltips), donut and sector bars, *Mix vs. reference*, and the *Past-shock test* in dollars. Read the rebalancing line ("trim about $...") and the tax note. Switch to `three_fund_beginner` and show the higher diversification score.
4. **Markets (40s).** Overview tiles with freshness labels; pick NVDA: price line with the 50-day average, 1M/3M change, volatility, biggest drop, and "What these numbers mean". Headlines with sentiment dots.
5. **Multi-agent hand-off (30s).** In chat: "Why is NVDA down today?" Market and news agents answer together; open *Sources and routing*.
6. **Goals and memory (50s).** In chat: "I want $50k for a down payment in 6 years, I have $10k saved and can invest $400 a month." Then click "What if I invest $500 a month?" and "What if I had 11 years instead?" to show context carried across turns. Show the Goals tab fan chart and change the risk profile.
7. **Files (40s).** Drag a bank-statement PDF or a photo of one into the chat with no text: get a summary and explained terms. Ask "how much did my balance change?" as a follow-up.
8. **Voice (20s).** Click the microphone, ask "What is an emergency fund?", show the "Transcribed from your voice message" tag.
9. **Resilience (20s).** No keys: sample data labelled as such, drafts instead of LLM text. Alpha Vantage limit: yFinance or stale cache, with labels.
10. **MCP (20s).** In Claude Desktop: "Use the finance assistant to show the price trend for VTI and project a $20k goal in 3 years."
11. **Quality (10s).** `pytest --cov`: all tests offline, about 96% coverage; `docs/rubric_map.md`.
