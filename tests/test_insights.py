"""Trend metrics, portfolio stress tests / rebalancing, goal agent and follow-up suggestions."""
import math

import pytest

from finance_assistant.utils.portfolio import STRESS_SCENARIOS, analyze_portfolio
from finance_assistant.utils.trends import annual_volatility, max_drawdown, trend_metrics
from finance_assistant.workflow.followups import suggest


def series(closes):
    return [{"date": f"d{i}", "close": c} for i, c in enumerate(closes)]


def test_trend_metrics_uptrend_and_returns():
    t = trend_metrics(series([100 * 1.002 ** i for i in range(120)]))
    assert t["trend"] == "uptrend" and t["vs_sma_50"] > 0 and t["max_drawdown"] == 0
    assert math.isclose(t["return_1m"], 1.002 ** 21 - 1, abs_tol=1e-4)  # metrics are rounded to 4 places
    assert t["volatility_level"] == "low" and any("uptrend" in s for s in t["summary"])


def test_trend_metrics_downtrend_and_drawdown():
    t = trend_metrics(series([200 - i for i in range(80)]))
    assert t["trend"] == "downtrend" and t["return_3m"] is not None
    assert t["max_drawdown"] == pytest.approx(121 / 200 - 1, abs=1e-4)
    assert any("biggest drop" in s for s in t["summary"])


def test_trend_metrics_short_and_tiny_series():
    assert trend_metrics(series([5.0]))["points"] == 1
    t = trend_metrics(series([10, 11, 12]))
    assert t["trend"] == "mixed" and t["return_1m"] is None and t["sma_50"] is None
    assert any("Past moves" in s for s in t["summary"])
    t30 = trend_metrics(series([10 + (i % 3) for i in range(30)]))  # a month of data, no 3-month figure
    assert any("about a month" in s for s in t30["summary"])
    assert annual_volatility([10.0, 11.0]) is None and max_drawdown([3, 2, 4, 1]) == pytest.approx(-0.75)


INFO = {"VTI": {"asset_class": "us_equity", "sector": "Broad Market"},
        "BND": {"asset_class": "bonds", "sector": "Fixed Income"}}


def test_stress_tests_and_rebalancing_amounts():
    a = analyze_portfolio([{"symbol": "VTI", "shares": 80}, {"symbol": "BND", "shares": 20}],
                          {"VTI": 100.0, "BND": 100.0}, INFO, cash=0, risk_profile="moderate")
    s2008 = next(s for s in a["stress_tests"] if s["scenario"].startswith("2008"))
    expected = 0.8 * STRESS_SCENARIOS["2008 financial crisis"]["us_equity"] + 0.2 * STRESS_SCENARIOS[
        "2008 financial crisis"]["bonds"]
    assert s2008["change_pct"] == pytest.approx(expected, abs=1e-4) and s2008["change_value"] == pytest.approx(expected * 10_000)
    # moderate reference: 42% US, 18% intl, 35% bonds, 5% cash -> trim US, add the rest; moves sum to zero
    assert a["rebalance"]["us_equity"] == pytest.approx(-3800) and a["rebalance"]["intl_equity"] == pytest.approx(1800)
    assert sum(a["rebalance"].values()) == pytest.approx(0, abs=0.05)
    assert a["return_to_risk"] > 0


def test_goal_agent_full_projection(workflow):
    r = workflow.chat("I want $40,000 for a down payment in 8 years, I have $8k saved and can invest $200 a month",
                      thread_id="t-goal-full")
    plan = r["results"][0]["data"]["plan"]
    assert r["agents"] == ["goal_planning"] and plan["target"] == 40_000 and plan["present"] == 8_000
    assert "monte_carlo" in plan and "Range of outcomes" in r["response"]
    assert "short of the goal" in r["response"] and "At that pace" in r["response"]
    short = workflow.chat("I need $12,000 in 2 years and can save $400 a month", thread_id="t-goal-short")
    assert "stable accounts" in short["response"]


def test_followups_are_specific_deduplicated_and_capped():
    plan = {"monthly_contribution": 350.0, "years": 6.0}
    out = suggest([{"agent": "goal_planning", "data": {"plan": plan}}], {}, "q")
    assert out[:2] == ["What if I invest $450 a month?", "What if I had 11 years instead?"] and len(out) == 3
    out = suggest([{"agent": "market_analysis", "data": {"tickers": ["NVDA"]}}], {"has_files": True}, "")
    assert out[0].startswith("Which financial terms") and "Any recent news on NVDA?" in out
    out = suggest([{"agent": "finance_qa", "data": {"glossary_terms": ["Exchange-Traded Fund (ETF)"]}}], {},
                  "Can you explain that with a simple example?")
    assert out[0] == 'Where would I run into "exchange-traded fund" in everyday life?'
    assert "Can you explain that with a simple example?" not in out
