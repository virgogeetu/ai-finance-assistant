"""Goal-planning math: deterministic projections and Monte Carlo simulation."""
from __future__ import annotations

import math
import random

RISK_RETURNS = {  # illustrative nominal return / volatility by risk profile
    "conservative": (0.045, 0.07),
    "moderate": (0.06, 0.11),
    "aggressive": (0.07, 0.15),
    "cash": (0.03, 0.005),
}


def future_value(present: float, monthly: float, annual_rate: float, years: float) -> float:
    n, r = round(years * 12), annual_rate / 12
    if r == 0:
        return present + monthly * n
    g = (1 + r) ** n
    return present * g + monthly * (g - 1) / r


def required_monthly(target: float, present: float, annual_rate: float, years: float) -> float:
    n, r = round(years * 12), annual_rate / 12
    if n <= 0:
        return max(0.0, target - present)
    if r == 0:
        return max(0.0, (target - present) / n)
    g = (1 + r) ** n
    return max(0.0, (target - present * g) * r / (g - 1))


def months_to_goal(target: float, present: float, monthly: float, annual_rate: float, cap_years: int = 80) -> int | None:
    bal, r = present, annual_rate / 12
    for m in range(cap_years * 12 + 1):
        if bal >= target:
            return m
        bal = bal * (1 + r) + monthly
    return None


def real_value(amount: float, inflation: float, years: float) -> float:
    return amount / (1 + inflation) ** years


def yearly_schedule(present: float, monthly: float, annual_rate: float, years: int) -> list[dict]:
    rows, contributed = [], present
    for y in range(0, years + 1):
        rows.append({"year": y, "balance": round(future_value(present, monthly, annual_rate, y), 2),
                     "contributed": round(contributed, 2)})
        contributed += monthly * 12
    return rows


def monte_carlo(present: float, monthly: float, years: int, mean: float, vol: float,
                target: float | None = None, sims: int = 1000, seed: int = 7) -> dict:
    """Lognormal monthly returns. Returns yearly percentile bands and success probability."""
    rng = random.Random(seed)
    months = years * 12
    mu = math.log(1 + mean) / 12 - (vol ** 2) / 24
    sig = vol / math.sqrt(12)
    paths_by_year = [[] for _ in range(years + 1)]
    finals = []
    for _ in range(sims):
        bal = present
        paths_by_year[0].append(bal)
        for m in range(1, months + 1):
            bal = bal * math.exp(rng.gauss(mu, sig)) + monthly
            if m % 12 == 0:
                paths_by_year[m // 12].append(bal)
        finals.append(bal)

    def pct(xs, p):
        xs = sorted(xs)
        return xs[min(len(xs) - 1, int(p * len(xs)))]

    bands = [{"year": y, "p10": round(pct(v, .10), 2), "p50": round(pct(v, .50), 2), "p90": round(pct(v, .90), 2)}
             for y, v in enumerate(paths_by_year)]
    out = {"bands": bands, "median_final": bands[-1]["p50"], "p10_final": bands[-1]["p10"],
           "p90_final": bands[-1]["p90"], "simulations": sims}
    if target is not None:
        out["success_probability"] = round(sum(f >= target for f in finals) / sims, 3)
    return out


def plan_goal(target: float, years: float, present: float = 0.0, monthly: float | None = None,
              risk_profile: str = "moderate", inflation: float = 0.025, simulate: bool = True,
              annual_return: float | None = None) -> dict:
    rate, vol = RISK_RETURNS.get(risk_profile, RISK_RETURNS["moderate"])
    label = risk_profile
    if years <= 3:  # short horizons: cash-like assumptions are more appropriate
        rate, vol = RISK_RETURNS["cash"]
        label = "cash (short horizon)"
    if annual_return is not None:  # the user's own assumption wins
        rate, label = annual_return, f"your {annual_return:.1%} assumption"
    years_i = max(1, round(years))
    need = required_monthly(target, present, rate, years)
    contrib = need if monthly is None else monthly
    projected = future_value(present, contrib, rate, years)
    result = {
        "target": target, "years": years, "present": present, "monthly_contribution": round(contrib, 2),
        "required_monthly": round(need, 2), "assumed_return": rate, "assumed_volatility": vol,
        "risk_profile": label,
        "projected_value": round(projected, 2), "on_track": projected >= target * 0.999,
        "target_in_todays_dollars": round(real_value(target, inflation, years), 2),
        "inflation_adjusted_target": round(target * (1 + inflation) ** years, 2),
        "schedule": yearly_schedule(present, contrib, rate, years_i),
    }
    if monthly is not None and not result["on_track"]:
        m = months_to_goal(target, present, monthly, rate)
        result["months_to_goal_at_current_rate"] = m
    if simulate and years > 3:
        result["monte_carlo"] = monte_carlo(present, contrib, years_i, rate, vol, target)
    return result
