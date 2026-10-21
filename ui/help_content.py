"""Text for the Help tab and the first-visit welcome tour (kept out of app.py so it is easy to edit)."""

TOUR = [
    ("What this app does",
     "AI Finance Assistant helps you **learn how money works** and look at **your own numbers** in plain language.\n\n"
     "- 💬 Ask questions about budgeting, investing, taxes or a stock\n"
     "- 📊 Get a review of your portfolio\n"
     "- 📈 See what the markets are doing\n"
     "- 🎯 Plan a savings goal\n\n"
     "It **teaches, it doesn't sell**: it never tells you what to buy or sell."),
    ("Where to start",
     "- **Ask**: type a question, click a starter question, or attach a file with **+** (PDF, photo, Excel…).\n"
     "- **Portfolio**: enter what you own and click **Analyze portfolio**.\n"
     "- **Markets**: pick a ticker to see its price trend, explained.\n"
     "- **Goals**: set a target and see your chance of reaching it.\n\n"
     "Set **Comfort with ups and downs** in the sidebar first; it shapes the portfolio and goal results."),
    ("Getting help",
     "- The **Help** tab explains every tab and number, has a searchable glossary of 100+ terms, and answers common questions.\n"
     "- Hover any **ⓘ** icon for a quick definition.\n"
     "- Under each answer, **Sources and routing** shows where the information came from, and the "
     "**You could ask next** buttons suggest a good next question.\n"
     "- Reopen this tour any time from the sidebar."),
]

QUICK_START = """
1. **Pick your comfort level** with ups and downs in the sidebar (conservative, moderate or aggressive).
2. **Ask a question** in the Ask tab, or click one of the starter questions.
3. **Follow up naturally**: after a goal plan, "what if I invest $500 a month?"; after a stock question, "any news on it?" The assistant remembers the conversation.
4. **Explore the other tabs** for your portfolio, the markets and your goals.
"""

TABS = {
    "💬 Ask": """
- Type any money question, or click a **starter question**.
- Attach files with **+** or drag them in: PDF, Word, Excel, CSV, text, or images. Send a file with no text to get a summary.
- If voice is set up, click the **microphone** to ask out loud.
- Under each answer: **Sources and routing** shows which specialist answered and the articles it used; **You could ask next** buttons suggest follow-ups.
- **Start a new conversation** (sidebar) clears the chat, its memory and attached files.
""",
    "📊 Portfolio": """
- Edit the table: **Ticker** (like VTI or AAPL), **Shares**, and optionally **Cost per share** to see your gain or loss.
- Add rows with the **+** at the bottom of the table; set your **Cash**.
- Click **Analyze portfolio** to see the metrics, four charts and a written explanation.
- Not sure what to enter? Load a **sample portfolio** from the sidebar.
""",
    "📈 Markets": """
- **Market overview**: index funds that stand in for the whole market (S&P 500, Nasdaq-100, Dow, small companies, international stocks, bonds, gold).
- **Price history**: pick a ticker to see six months of prices with a dotted 50-day average, plus trend numbers.
- **Headlines**: recent news for that ticker, with a mood tag (🟢 positive, 🔴 negative, ⚪ neutral).
""",
    "🎯 Goals": """
- Enter a **target**, the **years** until you need it, what you've **saved so far** and your **monthly contribution**.
- See the projected value, the monthly amount needed, and your **chance of reaching the goal** across 1,000 simulated markets.
- The shaded band shows the range from a bad-luck outcome (10th percentile) to a good-luck outcome (90th).
""",
}

METRICS = {
    "Diversification score (0–100)": "How spread out your money is across holdings, asset classes and sectors. Higher means one bad investment hurts less. Broad index funds score high.",
    "Est. volatility": "How much your portfolio's value typically swings in a year, based on long-run averages for each asset class. 10% means a typical year could be about 10% above or below average.",
    "Unrealized gain": "Profit or loss on paper: today's value minus what you paid. It becomes 'realized' (and possibly taxable) only when you sell.",
    "Return per unit of risk": "Expected return above cash, divided by volatility (a simplified Sharpe ratio). Higher means more expected reward for each bump along the way.",
    "Mix vs. reference": "Your mix of U.S. stocks, international stocks, bonds and cash next to a simple reference mix for your comfort level. Big gaps suggest rebalancing.",
    "Past-shock test": "Roughly how today's mix would have moved in the 2008 financial crisis, the 2020 COVID crash and the 2022 rate shock. A reality check, not a prediction.",
    "1-month / 3-month change": "How much the price moved over about 21 and 63 trading days.",
    "50-day average": "The average closing price over the last 50 trading days. It smooths out daily noise; price above it suggests a recent uptrend.",
    "Volatility (yearly)": "How much the price has swung, scaled to a year. Under 15% is calm, over 30% is bumpy.",
    "Biggest drop (max drawdown)": "The largest fall from a high point to a later low in the period shown. A 50% drop needs a 100% gain to recover.",
    "Chance of reaching goal": "The share of 1,000 simulated market paths that ended at or above your target. It reflects luck in returns, not a guarantee.",
    "Freshness labels": "Live = just fetched; Cached = fetched a few minutes ago; Stale = provider unavailable, last good value shown; Sample data = offline demo, not real prices.",
}

FAQ = {
    "Is this financial advice?":
        "No. It is an educational tool. It explains concepts and your own numbers but never tells you what to buy or sell. "
        "For decisions that depend on your full situation, talk to a licensed professional.",
    "Where do prices and news come from?":
        "From Alpha Vantage when an API key is set, then Yahoo Finance as a backup. If both are unavailable you'll see "
        "the last saved values (labelled Stale) or demo prices (labelled Sample data).",
    "Why do some answers say 'Sample data'?":
        "The app is running without live market data, either in offline mode or because the free data limit was reached. "
        "Sample prices are realistic-looking but not real.",
    "How does it remember my earlier questions?":
        "Each conversation keeps its own memory: the last stocks, goal and topic you discussed, plus any files you attached. "
        "Click 'Start a new conversation' in the sidebar to clear it.",
    "Why couldn't it read my image or scanned PDF?":
        "Pictures and scans are read by an AI model, so they need an AI provider configured (not offline mode). "
        "Typed PDFs, Word, Excel, CSV and text files are read locally and always work.",
    "Why are the numbers different from my brokerage?":
        "Prices may be delayed or cached, and the portfolio metrics use long-run asset-class averages, not your account's "
        "actual history. Use them to learn, not to reconcile your statement.",
    "Is my data private?":
        "Your portfolio and chat stay on the computer running the app; only ticker symbols are sent to the market-data "
        "provider to fetch prices. If an AI provider is configured, your questions and "
        "file contents are sent to that provider to generate answers, so don't upload account numbers or ID documents.",
    "Can I use it without internet or API keys?":
        "Yes. In offline mode it uses sample prices and builds answers directly from its knowledge base and calculators, "
        "without an AI model rewriting them.",
}

# ---- inline tips: tooltips (help=) and one-line "how to read this" captions -----------------------------------
TIPS = {
    # sidebar
    "risk": "How much your money can swing without you losing sleep. Conservative: steadier, slower growth. "
            "Aggressive: bigger ups and downs, more long-run growth. It sets the reference mix in Portfolio and the "
            "return assumptions in Goals.",
    "sample": "Ready-made example portfolios so you can explore without entering your own. Pick one, then click Load sample.",
    "load_sample": "Replaces the holdings and cash in the Portfolio tab with this example.",
    "new_chat": "Clears the chat, what the assistant remembers, and any attached files.",
    # ask
    "starter_tip": "💡 Tip: follow up naturally (\"what if I invest $500 a month?\", \"any news on it?\"). "
                   "Attach a statement or spreadsheet with **+** to ask about it.",
    "sources": "Which specialist answered, why it was chosen, and the articles or data it used. "
               "Numbers come from calculators and data feeds, not from the AI's imagination.",
    "next_question": "Ask this next",
    # portfolio
    "ticker": "The short code for a stock or fund, like VTI, AAPL or BND.",
    "shares": "How many shares you own. Fractions are fine, like 2.5.",
    "cost": "Optional: the average price you paid per share. Used to show your gain or loss.",
    "cash": "Uninvested money in the account. It counts toward your total and your mix.",
    "analyze": "Prices your holdings and explains your mix, risk and diversification.",
    "total_value": "Today's value of all holdings plus cash.",
    "read_donut": "💡 How your money splits across asset types. One big slice means less diversification.",
    "read_sector": "💡 Which parts of the economy you own. 'Broad Market' funds hold every sector at once.",
    "read_mix": "💡 Green is you, gold is a simple reference mix for your comfort level. Big gaps hint at rebalancing.",
    "read_shock": "💡 Rough change in today's value if a past crash happened again. Markets recovered each time, but it took a while.",
    "weight": "Share of your total portfolio in this holding.",
    "gain": "Change since you bought, based on your cost per share.",
    # markets
    "price_history": "Pick any ticker to see its last six months, its trend and its news.",
    "read_price": "💡 Green is the daily closing price; the dotted gold line is the 50-day average. "
                  "Price above the line suggests a recent uptrend, below it a downtrend.",
    "change_1m": "How much the price moved over about one month (21 trading days).",
    "change_3m": "How much the price moved over about three months (63 trading days).",
    "headlines": "💡 Sentiment tags describe the tone of the coverage (🟢 positive, 🔴 negative, ⚪ neutral), not where the price will go.",
    # goals
    "read_goal": "💡 The solid line is the typical (median) outcome; the shaded band is the likely range across 1,000 "
                 "simulated markets; the dotted line is what you put in. Where the band crosses the gold Goal line, "
                 "you're on track in many of the simulations.",
}

SAMPLE_NAMES = {
    "three_fund_beginner": "🌱 Three-fund beginner",
    "tech_heavy": "🚀 Tech-heavy",
    "retiree_income": "🏖️ Retiree income",
    "single_stock": "🏢 Single company stock",
}

OVERVIEW_TIPS = {
    "SPY": "S&P 500: about 500 of the largest U.S. companies. The most common 'how's the market?' benchmark.",
    "QQQ": "Nasdaq-100: 100 large non-financial companies, heavy in technology.",
    "DIA": "Dow Jones Industrial Average: 30 well-known U.S. companies.",
    "IWM": "Russell 2000: about 2,000 small U.S. companies.",
    "VXUS": "International stocks: thousands of companies outside the U.S.",
    "BND": "U.S. bonds: thousands of government and corporate bonds. Usually steadier than stocks.",
    "GLD": "Gold: tracks the price of gold bullion.",
}
