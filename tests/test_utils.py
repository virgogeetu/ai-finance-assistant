import math

from finance_assistant.utils.parsing import extract_tickers, parse_goal, parse_holdings
from finance_assistant.utils.portfolio import analyze_portfolio
from finance_assistant.utils.projections import (future_value, monte_carlo, months_to_goal, plan_goal,
                                                 required_monthly)


def test_future_value_matches_closed_form():
    assert math.isclose(future_value(1000, 0, 0.12, 1), 1000 * 1.01 ** 12, rel_tol=1e-9)
    assert future_value(0, 100, 0, 2) == 2400


def test_required_monthly_roundtrip():
    m = required_monthly(50_000, 5_000, 0.06, 8)
    assert math.isclose(future_value(5_000, m, 0.06, 8), 50_000, rel_tol=1e-6)


def test_months_to_goal():
    assert months_to_goal(1200, 0, 100, 0) == 12
    assert months_to_goal(1e12, 0, 1, 0.0) is None


def test_monte_carlo_is_deterministic_and_ordered():
    a = monte_carlo(1000, 100, 10, 0.06, 0.12, target=20000, sims=300)
    b = monte_carlo(1000, 100, 10, 0.06, 0.12, target=20000, sims=300)
    assert a == b
    assert a["p10_final"] <= a["median_final"] <= a["p90_final"]
    assert 0 <= a["success_probability"] <= 1


def test_short_horizon_uses_cash_assumptions():
    p = plan_goal(10_000, 2, 0, 300)
    assert p["assumed_return"] < 0.04 and "monte_carlo" not in p


INFO = {"VTI": {"asset_class": "us_equity", "sector": "Broad Market"},
        "BND": {"asset_class": "bonds", "sector": "Fixed Income"},
        "NVDA": {"asset_class": "us_equity", "sector": "Technology"}}


def test_portfolio_weights_and_flags():
    a = analyze_portfolio([{"symbol": "NVDA", "shares": 10}, {"symbol": "VTI", "shares": 1}],
                          {"NVDA": 100, "VTI": 100}, INFO, cash=0, risk_profile="moderate")
    assert math.isclose(sum(p["weight"] for p in a["positions"]), 1.0)
    assert any("NVDA" in f for f in a["flags"])
    assert any("international" in f.lower() for f in a["flags"])


def test_diversified_scores_higher_than_concentrated():
    div = analyze_portfolio([{"symbol": "VTI", "shares": 6}, {"symbol": "BND", "shares": 4}],
                            {"VTI": 100, "BND": 100}, INFO)
    conc = analyze_portfolio([{"symbol": "NVDA", "shares": 10}], {"NVDA": 100}, INFO)
    assert div["diversification_score"] > conc["diversification_score"]
    assert div["expected_volatility"] < conc["expected_volatility"]


def test_unpriced_and_empty():
    a = analyze_portfolio([{"symbol": "ZZZ", "shares": 1}], {}, {})
    assert a["total_value"] == 0 and a["unpriced"] == ["ZZZ"]


def test_parsing():
    assert extract_tickers("Is AAPL better than an ETF in my IRA?") == ["AAPL"]
    assert extract_tickers("compare $XYZ and MSFT", known={"MSFT"}) == ["XYZ", "MSFT"]
    g = parse_goal("I want $50k for a house in 6 years, I have $10,000 saved and can add $400 a month")
    assert g == {"years": 6.0, "target": 50_000, "present": 10_000, "monthly": 400}
    h = parse_holdings("I own 10 VTI, 5 shares of BND and AAPL: 3")
    assert {x["symbol"]: x["shares"] for x in h} == {"VTI": 10, "BND": 5, "AAPL": 3}


def test_parse_goal_ignores_age_and_keeps_rate():
    g = parse_goal("I'm 30 years old and want $1,000,000 in 25 years assuming 8% return")
    assert g["years"] == 25 and g["rate"] == 0.08 and g["target"] == 1_000_000


def test_plan_goal_uses_stated_return():
    assert plan_goal(50_000, 10, annual_return=0.08)["assumed_return"] == 0.08


def test_parse_goal_to_have_is_the_target():
    g = parse_goal("How much should I save monthly to have $1,000,000 in 25 years? I have $20k saved")
    assert g["target"] == 1_000_000 and g["present"] == 20_000
