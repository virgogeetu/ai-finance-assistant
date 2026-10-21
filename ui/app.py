"""Streamlit UI: chat, portfolio dashboard, market overview, goal planner.

Run:  streamlit run ui/app.py
"""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "ui"))

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

from finance_assistant import DISCLAIMER
from finance_assistant.core.attachments import SUPPORTED_TYPES, read_file
from finance_assistant.utils.parsing import fmt_money
from finance_assistant.utils.projections import plan_goal
from finance_assistant.utils.trends import trend_metrics
from finance_assistant.workflow import FinanceWorkflow
from help_content import FAQ, METRICS, OVERVIEW_TIPS, QUICK_START, SAMPLE_NAMES, TABS, TIPS, TOUR

# "Soft and friendly" palette; matches .streamlit/config.toml
INK, GREEN, BRASS, ROSE, MIST = "#2B3A42", "#3E8E6E", "#E0A458", "#E07A6F", "#B8CFC7"
CLASS_COLORS = {"us_equity": GREEN, "intl_equity": "#5B9BD5", "bonds": BRASS, "real_estate": "#9B84C9",
                "commodities": "#D9B779", "cash": MIST, "other": "#A9B4BB"}
TAB_ASK, TAB_PORTFOLIO, TAB_MARKETS, TAB_GOALS, TAB_HELP = "💬 Ask", "📊 Portfolio", "📈 Markets", "🎯 Goals", "❓ Help"
CLASS_NAMES = {"us_equity": "U.S. stocks", "intl_equity": "International stocks", "bonds": "Bonds",
               "real_estate": "Real estate", "commodities": "Commodities", "cash": "Cash", "other": "Other"}

st.set_page_config(page_title="AI Finance Assistant", page_icon="🌱", layout="wide")
pio.templates["soft"] = go.layout.Template(layout=dict(
    font=dict(family="Nunito, sans-serif", color=INK, size=14),
    colorway=[GREEN, "#5B9BD5", BRASS, ROSE, "#9B84C9", "#D9B779", MIST],
    xaxis=dict(gridcolor="#EEE6DA", zerolinecolor="#E6DDD0"), yaxis=dict(gridcolor="#EEE6DA", zerolinecolor="#E6DDD0")))
pio.templates.default = "plotly_white+soft"  # every chart picks up the soft palette and rounded font
st.markdown("""
<style>
/* soft cards for metrics and chat messages */
[data-testid="stMetric"] { background: #FFFFFF; border: 1px solid #E6DDD0; border-radius: 1rem;
  padding: .8rem 1rem; box-shadow: 0 1px 3px rgba(43,58,66,.06); }
[data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; }
[data-testid="stChatMessage"] { background: #FFFFFF; border: 1px solid #EEE6DA; border-radius: 1.25rem;
  padding: .9rem 1.1rem; box-shadow: 0 1px 3px rgba(43,58,66,.05); }
[data-testid="stExpander"] details { border-radius: 1rem; }
/* roomier, friendlier tabs */
[data-testid="stTabs"] button[role="tab"] p { font-size: 1.05rem; font-weight: 700; }
.freshness { font-size: .85rem; color: #5A6870; background: #FFF6E8; border-radius: .75rem;
  padding: .45rem .8rem; display: inline-block; }
.hello { font-size: 1.1rem; color: #4A5A63; margin-top: -.5rem; margin-bottom: 1rem; }
</style>""", unsafe_allow_html=True)


@st.cache_resource(show_spinner="Loading knowledge base…")
def get_workflow() -> FinanceWorkflow:
    return FinanceWorkflow()


@st.cache_data
def sample_portfolios() -> dict:
    return json.loads((ROOT / "knowledge_base" / "sample_portfolios.json").read_text())


wf = get_workflow()
ss = st.session_state
ss.setdefault("thread_id", str(uuid.uuid4()))
ss.setdefault("chat", [])
ss.setdefault("holdings", pd.DataFrame(sample_portfolios()["three_fund_beginner"]["holdings"]))
ss.setdefault("cash", 1500.0)

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("### Your profile")
    risk = st.radio("Comfort with ups and downs", ["conservative", "moderate", "aggressive"], index=1,
                    help=TIPS["risk"])
    st.markdown("### Sample portfolios")
    choice = st.selectbox("Load a sample", ["—"] + list(sample_portfolios()), help=TIPS["sample"],
                          format_func=lambda k: SAMPLE_NAMES.get(k, k))
    if choice != "—":
        st.caption(sample_portfolios()[choice].get("description", ""))
    if choice != "—" and st.button("Load sample", help=TIPS["load_sample"]):
        p = sample_portfolios()[choice]
        ss.holdings, ss.cash = pd.DataFrame(p["holdings"]), float(p["cash"])
        st.rerun()
    if st.button("Start a new conversation", help=TIPS["new_chat"]):
        ss.thread_id, ss.chat = str(uuid.uuid4()), []
        st.rerun()
    st.markdown("### Need help?")
    h1, h2 = st.columns(2)
    if h1.button("👋 Tour", help="Show the 3-step welcome tour again", width="stretch"):
        ss.tour_step, ss.show_tour = 0, True
    if h2.button("📖 Help", help="Open the Help tab: guides, glossary and FAQ", width="stretch"):
        ss.goto_tab = TAB_HELP
    st.divider()
    status = wf.market.status()
    st.caption(f"Model: **{wf.llm.provider}** {'(offline drafts)' if wf.llm.is_mock else wf.settings.model_name}")
    st.caption(f"Market data: {', '.join(status['providers'])}")
    st.caption(f"Search index: {wf.retriever.store.backend}, {len(wf.retriever.store.chunks)} passages")
    st.caption(f"Orchestrator: {wf.engine}")


def no_math(text: str) -> str:
    """Escape $ so amounts like "$1,500 … $450" aren't rendered as a LaTeX formula."""
    return text.replace("$", r"\$")


@st.dialog("Welcome to AI Finance Assistant 👋", width="large")
def welcome_tour():
    step = ss.get("tour_step", 0)
    title, body = TOUR[step]
    st.progress((step + 1) / len(TOUR), text=f"Step {step + 1} of {len(TOUR)}")
    st.markdown(f"#### {title}")
    st.markdown(no_math(body))
    back, skip, nxt = st.columns(3)
    if step > 0 and back.button("← Back", width="stretch"):
        ss.tour_step = step - 1
        st.rerun(scope="fragment")
    if step < len(TOUR) - 1:
        if skip.button("Skip tour", width="stretch"):
            st.rerun()
        if nxt.button("Next →", type="primary", width="stretch"):
            ss.tour_step = step + 1
            st.rerun(scope="fragment")
    else:
        if skip.button("Open the Help tab", width="stretch"):
            ss.goto_tab = TAB_HELP
            st.rerun()
        if nxt.button("Start exploring", type="primary", width="stretch"):
            st.rerun()


if not ss.get("tour_seen"):  # first visit in this browser session
    ss.tour_seen, ss.show_tour, ss.tour_step = True, True, 0
if ss.pop("show_tour", False):
    welcome_tour()


def current_portfolio() -> dict:
    df = ss.holdings.dropna(subset=["symbol"])
    holdings = [{"symbol": str(r.symbol).upper().strip(), "shares": float(r.shares or 0),
                 "cost_basis": float(r.cost_basis) if "cost_basis" in df and pd.notna(r.cost_basis) else None}
                for r in df.itertuples() if str(r.symbol).strip()]
    return {"holdings": holdings, "cash": float(ss.cash), "risk_profile": risk}


st.title("🌱 AI Finance Assistant")
st.markdown("<div class='hello'>Hi there 👋 Learn how money works, check your portfolio and plan your goals, "
            "all in plain language.</div>", unsafe_allow_html=True)
if "goto_tab" in ss:  # buttons elsewhere can switch tabs; must happen before the tabs are drawn
    ss.main_tabs = ss.pop("goto_tab")
tab_chat, tab_port, tab_mkt, tab_goal, tab_help = st.tabs([TAB_ASK, TAB_PORTFOLIO, TAB_MARKETS, TAB_GOALS, TAB_HELP],
                                                           key="main_tabs", on_change="rerun")

# ---------------------------------------------------------------- chat
with tab_chat:
    if not ss.chat:
        st.markdown("#### What would you like to learn today?\nTry one of these, or type your own question below.")
        cols = st.columns(3)
        starters = ["What's the difference between a Roth and traditional IRA?",
                    "Review my portfolio", "How much do I need to save monthly for $30k in 4 years?"]
        for col, q in zip(cols, starters, strict=True):
            if col.button(q, width="stretch"):
                ss.pending_q = q
        st.caption(TIPS["starter_tip"])
    for i, m in enumerate(ss.chat):
        with st.chat_message(m["role"]):
            st.markdown(no_math(m["content"]))
            if m.get("voice"):
                st.caption("🎙️ Transcribed from your voice message")
            for f in m.get("files", []):
                st.caption(f"📎 {f['name']}" + (f" · {f['note']}" if f.get("note") else ""))
            if m.get("meta"):
                with st.expander("Sources and routing"):
                    st.caption(TIPS["sources"])
                    st.caption(f"Answered by: {', '.join(m['meta']['agents'])} · {m['meta']['route_reason']}")
                    for n, src in enumerate(m["meta"]["sources"], 1):
                        label = src.get("title", "source")
                        st.markdown(f"{n}. [{label}]({src['url']})" if src.get("url") else f"{n}. {label}")
            if i == len(ss.chat) - 1 and m.get("suggestions"):  # next-step ideas under the latest answer
                st.caption("You could ask next:")
                for j, sq in enumerate(m["suggestions"]):
                    if st.button(sq, key=f"next-{i}-{j}", help=TIPS["next_question"]):
                        ss.pending_q = sq
    voice_ok = wf.llm.can_transcribe
    submitted = st.chat_input("Ask, " + ("speak, " if voice_ok else "") + "or attach a PDF, image or spreadsheet",
                              accept_file="multiple", file_type=SUPPORTED_TYPES, max_upload_size=25,
                              accept_audio=voice_ok)
    voice = False
    if submitted is None:
        question, uploads = ss.pop("pending_q", None), []
    else:
        question, uploads = submitted.text or "", list(submitted.files or [])
        audio = getattr(submitted, "audio", None)
        if audio is not None and not question.strip():
            with st.spinner("Listening…"):
                question = wf.llm.transcribe(audio.getvalue(), getattr(audio, "name", "") or "question.wav")
            voice = bool(question)
            if not question:
                st.warning("Sorry, I couldn't make out that recording. Please try again or type your question.")
        if uploads and not question.strip():
            question = "Summarize the attached file(s) in plain language and explain any financial terms in them."
    if question:
        files = []
        if uploads:
            with st.spinner("Reading files…"):
                files = [read_file(f.name, f.getvalue(), wf.llm) for f in uploads]
        ss.chat.append({"role": "user", "content": question, "voice": voice,
                        "files": [{"name": d["name"], "note": d["note"]} for d in files]})
        with st.spinner("Thinking…"):
            r = wf.chat(question, ss.thread_id, portfolio=current_portfolio(), user_profile={"risk_profile": risk},
                        attachments=files or None)
        ss.chat.append({"role": "assistant", "content": r["response"],
                        "suggestions": r.get("suggestions", []),
                        "meta": {"agents": r["agents"], "route_reason": r["route_reason"], "sources": r["sources"]}})
        st.rerun()

# ---------------------------------------------------------------- portfolio
with tab_port:
    left, right = st.container(), st.container()  # stacked: holdings on top, full-width results below
    with left:
        st.subheader("Holdings")
        ss.holdings = st.data_editor(ss.holdings, num_rows="dynamic", width="stretch", key="editor",
                                     column_config={
                                         "symbol": st.column_config.TextColumn("Ticker", help=TIPS["ticker"]),
                                         "shares": st.column_config.NumberColumn("Shares", min_value=0,
                                                                                 help=TIPS["shares"]),
                                         "cost_basis": st.column_config.NumberColumn("Cost per share", format="$%.2f",
                                                                                     help=TIPS["cost"])})
        st.caption("Click a cell to edit; add a row with **+** at the bottom of the table.")
        ss.cash = st.number_input("Cash", min_value=0.0, value=float(ss.cash), step=100.0, help=TIPS["cash"])
        run = st.button("Analyze portfolio", type="primary", help=TIPS["analyze"])
    with right:
        if run or ss.get("analysis"):
            if run:
                with st.spinner("Pricing holdings…"):
                    res = wf.agents["portfolio_analysis"].run(
                        {"query": "review my portfolio", "portfolio": current_portfolio(),
                         "user_profile": {"risk_profile": risk}, "messages": []})
                ss.analysis = res
            res = ss.analysis
            a = (res.get("data") or {}).get("analysis")
            if not a:
                st.info(res.get("content") or "Add at least one holding to analyze.")
            else:
                (c1, c2), (c3, c4) = st.columns(2), st.columns(2)  # 2x2 so values never get cut off
                c1.metric("Total value", fmt_money(a["total_value"]), help=TIPS["total_value"])
                c2.metric("Diversification", f"{a['diversification_score']}/100",
                          help="0–100. Higher means your money is spread across more holdings, asset classes and sectors.")
                c3.metric("Est. volatility", f"{a['expected_volatility']:.1%}",
                          help="How much the portfolio's value typically swings in a year, from long-run asset-class "
                               "assumptions. Bigger number, bumpier ride.")
                c4.metric("Unrealized gain", fmt_money(a["unrealized_gain"]) if a["unrealized_gain"] is not None else "—",
                          help="Profit or loss on paper versus what you paid (needs cost per share).")
                cls = a["allocation_by_class"]
                donut = go.Figure(go.Pie(labels=[CLASS_NAMES.get(k, k) for k in cls], values=list(cls.values()), hole=.6,
                                         marker_colors=[CLASS_COLORS.get(k, MIST) for k in cls], sort=False))
                donut.update_layout(title="By asset class", height=300, margin=dict(t=40, b=0, l=8, r=8),
                                    legend=dict(orientation="h", y=-0.1),
                                    paper_bgcolor="rgba(0,0,0,0)", font_color=INK)
                sec = a["allocation_by_sector"]
                bars = go.Figure(go.Bar(x=list(sec.values()), y=list(sec), orientation="h", marker_color=GREEN))
                bars.update_layout(title="By sector", height=300, xaxis_tickformat=".0%",
                                   yaxis=dict(autorange="reversed", automargin=True),
                                   margin=dict(t=40, b=0, l=8, r=8), paper_bgcolor="rgba(0,0,0,0)",
                                   plot_bgcolor="rgba(0,0,0,0)", font_color=INK)
                g1, g2 = st.columns(2)
                g1.plotly_chart(donut, width="stretch")
                g1.caption(TIPS["read_donut"])
                g2.plotly_chart(bars, width="stretch")
                g2.caption(TIPS["read_sector"])
                g3, g4 = st.columns(2)
                classes = [c for c in CLASS_NAMES if c in a["target_allocation"] or c in cls]
                mix = go.Figure([
                    go.Bar(name="Your mix", x=[CLASS_NAMES[c] for c in classes], y=[cls.get(c, 0) for c in classes],
                           marker_color=GREEN),
                    go.Bar(name=f"Reference ({a['risk_profile']})", x=[CLASS_NAMES[c] for c in classes],
                           y=[a["target_allocation"].get(c, 0) for c in classes], marker_color=BRASS)])
                mix.update_layout(title="Mix vs. reference", xaxis=dict(automargin=True), barmode="group", height=300,
                                  yaxis_tickformat=".0%",
                                  margin=dict(t=40, b=0, l=8, r=8), paper_bgcolor="rgba(0,0,0,0)",
                                  plot_bgcolor="rgba(0,0,0,0)", font_color=INK, legend=dict(orientation="h", y=-0.25))
                g3.plotly_chart(mix, width="stretch")
                g3.caption(TIPS["read_mix"])
                stress = a.get("stress_tests") or []
                short = {"2008 financial crisis": "2008 crisis", "2020 COVID crash": "2020 COVID",
                         "2022 rate shock": "2022 rates"}
                shock = go.Figure(go.Bar(x=[t["change_pct"] for t in stress],
                                         y=[short.get(t["scenario"], t["scenario"]) for t in stress],
                                         orientation="h", text=[fmt_money(t["change_value"]) for t in stress],
                                         marker_color=[ROSE if t["change_pct"] < 0 else GREEN for t in stress]))
                shock.update_layout(title="Past-shock test", height=300, xaxis_tickformat=".0%",
                                    yaxis=dict(autorange="reversed", automargin=True), margin=dict(t=40, b=0, l=8, r=8),
                                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=INK)
                g4.plotly_chart(shock, width="stretch")
                g4.caption(TIPS["read_shock"])
                if a.get("return_to_risk") is not None:
                    st.caption(f"Return per unit of risk: **{a['return_to_risk']:.2f}** (a simplified Sharpe ratio). "
                               "Past-shock test: how today's mix would have moved in the 2008 crisis, the 2020 COVID "
                               "crash and the 2022 rate shock. Rough estimates, not predictions.")
                st.dataframe(pd.DataFrame([{"Ticker": p["symbol"], "Name": p["name"], "Shares": p["shares"],
                                            "Price": p["price"], "Value": round(p["value"], 2), "Weight": f"{p['weight']:.1%}",
                                            "Gain": p["gain_pct"] and f"{p['gain_pct']:+.1%}"} for p in a["positions"]]),
                             hide_index=True, width="stretch",
                             column_config={"Weight": st.column_config.TextColumn("Weight", help=TIPS["weight"]),
                                            "Gain": st.column_config.TextColumn("Gain", help=TIPS["gain"])})
                with st.expander("What this means", expanded=True):
                    st.markdown(no_math(res["content"]))

# ---------------------------------------------------------------- markets
with tab_mkt:
    if tab_mkt.open is not False:  # only fetch prices when this tab is showing, to save API calls
        st.subheader("Market overview")
        ov = wf.market.market_overview()
        labels, items = set(), list(ov.items())
        cols = [c for i in range(0, len(items), 4) for c in st.columns(4)]  # rows of 4 so prices fit on narrow screens
        for col, (sym, q) in zip(cols, items, strict=False):
            if "price" in q:
                col.metric(sym, f"${q['price']:,.2f}", f"{q['change_percent']:+.2f}%", help=OVERVIEW_TIPS.get(sym))
                labels.add(q["freshness"]["label"])
            else:
                col.metric(sym, "—", help=OVERVIEW_TIPS.get(sym))
        st.markdown(f"<div class='freshness'>{' · '.join(sorted(labels))}</div>", unsafe_allow_html=True)
        sym = st.selectbox("Price history", sorted(wf.market.securities), index=sorted(wf.market.securities).index("SPY"),
                           help=TIPS["price_history"],
                           format_func=lambda t: f"{t} · {wf.market.info(t).get('name', '')}".rstrip(" ·"))
        hist = wf.market.get_daily(sym)
        df = pd.DataFrame(hist["series"])
        df["sma50"] = df["close"].rolling(50).mean()
        df = df.tail(120)
        fig = go.Figure([go.Scatter(x=df["date"], y=df["close"], mode="lines", name="Close", line=dict(color=GREEN, width=2)),
                         go.Scatter(x=df["date"], y=df["sma50"], mode="lines", name="50-day average",
                                    line=dict(color=BRASS, width=1.5, dash="dot"))])
        fig.update_layout(height=340, margin=dict(t=10, b=0, l=8, r=8), yaxis_tickprefix="$",
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=INK,
                          legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig, width="stretch")
        st.caption(TIPS["read_price"])
        st.caption(hist["freshness"]["label"])
        t = trend_metrics(hist["series"])
        if t["points"] >= 2:
            pct = lambda v: f"{v:+.1%}" if v is not None else "—"  # noqa: E731
            (m1, m2), (m3, m4) = st.columns(2), st.columns(2)  # 2x2 so values never get cut off
            m1.metric("1-month change", pct(t["return_1m"]), help=TIPS["change_1m"])
            m2.metric("3-month change", pct(t["return_3m"]), help=TIPS["change_3m"])
            m3.metric("Volatility (yearly)", f"{t['annual_volatility']:.0%}" if t.get("annual_volatility") else "—",
                      help="How much the price has swung, scaled to a year. Under 15% is calm, over 30% is bumpy.")
            m4.metric("Biggest drop", f"{t['max_drawdown']:.0%}",
                      help="Largest fall from a high point to a later low in this window (max drawdown).")
            with st.expander("What these numbers mean", expanded=False):
                st.markdown(no_math("\n".join(f"- {line}" for line in t["summary"])))
        st.subheader(f"Headlines for {sym}")
        st.caption(TIPS["headlines"])
        news = wf.market.get_news([sym])
        for n in news["articles"][:6]:
            title = f"[{n['title']}]({n['url']})" if n["url"] else n["title"]
            mood = "🟢" if "Bullish" in n["sentiment_label"] else "🔴" if "Bearish" in n["sentiment_label"] else "⚪"
            st.markdown(no_math(f"- {title} — {n['source']} · {mood} {n['sentiment_label']}"))

# ---------------------------------------------------------------- goals
with tab_goal:
    st.subheader("Plan a goal")
    (a, b), (c, d) = st.columns(2), st.columns(2)
    target = a.number_input("Target amount ($)", min_value=1000.0, value=50000.0, step=1000.0,
                            help="How much you want to have saved.")
    years = b.number_input("Years from now", min_value=1, max_value=60, value=8, help="When you need the money.")
    present = c.number_input("Saved so far ($)", min_value=0.0, value=5000.0, step=500.0,
                             help="Money already set aside for this goal.")
    monthly = d.number_input("Monthly contribution ($)", min_value=0.0, value=350.0, step=25.0,
                             help="How much you plan to add each month.")
    plan = plan_goal(target, years, present, monthly, risk)
    put_in = present + monthly * 12 * years
    mc = plan.get("monte_carlo")
    (m1, m2), (m3, m4) = st.columns(2), st.columns(2)  # 2x2 so values never get cut off
    m1.metric("Projected value", fmt_money(plan["projected_value"]),
              f"{fmt_money(plan['projected_value'] - target)} vs goal",
              help="What you'd have with average returns. Real results will vary.")
    m2.metric("Monthly needed", fmt_money(plan["required_monthly"]),
              help="The monthly amount that reaches the target with average returns.")
    m3.metric("Chance of reaching goal", f"{mc['success_probability']:.0%}" if mc else "—",
              help="Share of 1,000 simulated market paths that ended at or above the target.")
    m4.metric("Money you put in", fmt_money(put_in),
              f"growth adds {fmt_money(plan['projected_value'] - put_in)}",
              help="Your savings so far plus all monthly contributions; the rest of the projected value is growth.")
    fig = go.Figure()
    if mc:
        yrs = [r["year"] for r in mc["bands"]]
        fig.add_trace(go.Scatter(x=yrs, y=[r["p90"] for r in mc["bands"]], mode="lines", line=dict(width=0), showlegend=False,
                                 hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=yrs, y=[r["p10"] for r in mc["bands"]], mode="lines", fill="tonexty",
                                 fillcolor="rgba(62,142,110,0.15)",
                                 line=dict(width=0), name="Likely range (10th–90th)"))
        fig.add_trace(go.Scatter(x=yrs, y=[r["p50"] for r in mc["bands"]], mode="lines", line=dict(color=GREEN, width=2.5),
                                 name="Median"))
    fig.add_trace(go.Scatter(x=[r["year"] for r in plan["schedule"]], y=[r["contributed"] for r in plan["schedule"]],
                             mode="lines", line=dict(color=MIST, dash="dot", width=2), name="Money you put in"))
    fig.add_hline(y=target, line_color=BRASS, annotation_text="Goal")
    fig.update_layout(height=380, xaxis_title="Years", yaxis_tickprefix="$", margin=dict(t=10, b=0, l=8, r=8),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=INK,
                      legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, width="stretch")
    st.caption(TIPS["read_goal"])
    st.caption(f"Assumes {plan['assumed_return']:.1%} average annual return and {plan['assumed_volatility']:.0%} volatility "
               f"({plan['risk_profile']}). Illustrative only.")

# ---------------------------------------------------------------- help
with tab_help:
    st.subheader("How to use AI Finance Assistant")
    st.markdown(QUICK_START)
    if st.button("👋 Replay the welcome tour"):
        ss.tour_step = 0
        welcome_tour()

    st.subheader("What each tab does")
    for name, text in TABS.items():
        with st.expander(name):
            st.markdown(no_math(text))

    st.subheader("What the numbers mean")
    for name, text in METRICS.items():
        with st.expander(name):
            st.markdown(no_math(text))

    st.subheader("Glossary")
    glossary = wf.retriever.glossary
    query = st.text_input("Search the glossary", placeholder="e.g. ETF, compound interest, APR",
                          help="Searches term names and definitions.").strip().lower()
    hits = sorted((t, d) for t, d in glossary.items() if not query or query in t.lower() or query in d.lower())
    shown = hits if query else hits[:20]
    st.caption(f"{len(hits)} of {len(glossary)} terms match" if query
               else f"Showing 20 of {len(glossary)} terms. Type above to search them all.")
    if query and not hits:
        st.info("No matching term. Try a shorter word, or ask your question in the Ask tab.")
    for term, definition in shown:
        with st.expander(term):
            st.markdown(no_math(definition))
            if st.button("Ask about this in chat", key=f"ask-{term}"):
                ss.pending_q = f"Explain {term} in simple terms with an example."
                ss.goto_tab = TAB_ASK
                st.rerun()

    st.subheader("Common questions")
    for question, answer in FAQ.items():
        with st.expander(question):
            st.markdown(no_math(answer))

st.divider()
st.caption(DISCLAIMER.strip("_"))
