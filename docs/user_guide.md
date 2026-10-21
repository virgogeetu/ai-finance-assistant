# User guide

AI Finance Assistant helps you learn how money works and look at your own numbers in plain language. It explains; it does not tell you what to buy or sell.

Start it with `streamlit run ui/app.py` and open the address it prints (usually http://localhost:8501).

## Welcome tour and Help

The first time you open the app, a **3-step welcome tour** explains what it does, where to start and how to get help. Use **Next**, **Back** or **Skip tour**, or close it with ✕. Reopen it any time with **👋 Tour** in the sidebar.

The **Help** tab (or **📖 Help** in the sidebar) has:
- a quick-start guide and a short explanation of each tab
- what every number means (diversification score, volatility, drawdown, chance of reaching a goal, freshness labels…)
- a **searchable glossary** of 104 terms; open a term and click **Ask about this in chat** to get a fuller explanation
- answers to common questions, such as whether this is financial advice and how your data is handled

### Tips on every screen

Hover any **ⓘ** icon for a one-line definition: every metric, input, sample portfolio, market-overview ticker and holdings-table column has one. Lines starting with 💡 under each chart explain how to read it.

## The sidebar

- **Comfort with ups and downs** (conservative, moderate, aggressive). This sets the reference mix used in the portfolio review and the return assumptions in goal projections. Change it at any time.
- **Sample portfolios.** Load a ready-made portfolio to explore without typing your own.
- **Start a new conversation.** Clears the chat, its memory and any files you attached.
- **Need help?** Replay the welcome tour, or jump to the Help tab.
- The bottom lines show what is running: the AI model (or "mock" for offline drafts), the market-data source, the size of the knowledge base, and the orchestrator.

## Ask (chat)

Type a question, click one of the starter questions, or use the buttons under each answer.

| You can… | Example |
|---|---|
| Learn a concept | "What's the difference between an ETF and a mutual fund?" |
| Review your portfolio | "Review my portfolio" (uses the Portfolio tab) or "I own 10 VTI, 5 BND and 3 AAPL" |
| Check a stock or the market | "How is AAPL doing?", "How's the market today?" |
| Understand a move | "Why is NVDA down today?" (market and news agents answer together) |
| Plan a goal | "I want $40,000 in 5 years, I have $8k saved and can invest $400 a month" |
| Ask about taxes and accounts | "How does a Roth IRA work?", "What is a wash sale?" |

**Follow-ups remember the conversation.** After a goal plan, ask "What if I invest $500 a month?" or "What if I had 10 years instead?" and the assistant reuses the rest of your goal. After a stock question, "any news on it?" knows which stock you meant.

**Suggested next questions** appear as buttons under the latest answer. They are picked from what you just asked, such as a news check after a stock quote.

**Sources and routing.** Open this under any answer to see which specialist answered, the knowledge-base articles it used (with links) and where market data came from.

### Attaching files

Click **+** in the chat box, or drag files onto it. Supported: PDF, Word (.docx), Excel (.xlsx), CSV, JSON, text and Markdown, and images (PNG, JPG, WEBP, GIF), up to 25 MB each. Send files without a question to get a plain-language summary. Files stay with the conversation, so you can keep asking about them.

Images and scanned PDFs are read by the AI model, so they need an LLM provider set up (not offline mode). Check important numbers against the original.

### Voice questions

When an OpenAI key is configured, the chat box shows a microphone. Record your question and it is transcribed and answered like typed text. The message is marked "Transcribed from your voice message".

## Portfolio

Edit the holdings table (ticker, shares, optional cost per share), set your cash, and click **Analyze portfolio**.

| You'll see | What it means |
|---|---|
| Total value, unrealized gain | What it's worth now, and the paper profit or loss versus what you paid |
| Diversification score (0–100) | How spread out your money is across holdings, asset classes and sectors |
| Est. volatility | How much the value typically swings in a year (from long-run asset-class assumptions) |
| By asset class / by sector | Where your money sits |
| Mix vs. reference | Your mix next to a simple reference mix for your comfort level |
| Past-shock test | Roughly how today's mix would have moved in the 2008 crisis, the 2020 COVID crash and the 2022 rate shock |
| What this means | A written explanation, including concentration warnings and what rebalancing would look like in dollars |

Hover the ⓘ icons for short definitions.

## Markets

- **Market overview.** Broad index ETFs as a stand-in for the market (S&P 500, Nasdaq-100, Dow, small caps, international stocks, bonds, gold).
- **Price history.** Pick a ticker to see six months of prices with a 50-day average line, plus the 1- and 3-month change, volatility and biggest drop. "What these numbers mean" explains each one.
- **Headlines.** Recent news for that ticker with a sentiment tag (🟢 positive, 🔴 negative, ⚪ neutral) when available.

Every price shows how fresh it is: **Live**, **Cached** (fetched a few minutes ago), **Stale** (the provider is unavailable, so the last good value is shown), or **Sample data** (offline demo, not real prices).

## Goals

Enter a target, years, savings so far and monthly contribution. You'll see four cards: the projected value, the monthly amount needed, the share of 1,000 simulated market paths that reached the goal, and **money you put in** (with how much growth adds on top). The shaded band shows the 10th–90th percentile range. Goals of 3 years or less use cash-like assumptions, because stocks are risky over short periods.

## Good to know

- All projections and stress tests use illustrative assumptions, not forecasts.
- With a real AI model configured, your questions and file contents are sent to that provider. Don't upload full account numbers or ID documents.
- For decisions that depend on your full situation, talk to a licensed professional.
