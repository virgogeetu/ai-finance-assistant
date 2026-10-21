"""Portfolio analytics (pure functions, no I/O).

Return/volatility figures use simple, illustrative long-run capital-market
assumptions (CMAs) per asset class. They are for education, not forecasts.
"""
from __future__ import annotations

import math

# expected annual return, annual volatility (illustrative)
CMA = {
    "us_equity": (0.07, 0.16),
    "intl_equity": (0.07, 0.17),
    "bonds": (0.04, 0.06),
    "real_estate": (0.06, 0.19),
    "commodities": (0.03, 0.15),
    "cash": (0.03, 0.005),
    "other": (0.06, 0.20),
}
_CORR = {
    ("us_equity", "intl_equity"): 0.8, ("us_equity", "bonds"): 0.1, ("intl_equity", "bonds"): 0.1,
    ("us_equity", "real_estate"): 0.7, ("intl_equity", "real_estate"): 0.6, ("bonds", "real_estate"): 0.2,
    ("us_equity", "commodities"): 0.2, ("intl_equity", "commodities"): 0.3, ("bonds", "commodities"): 0.0,
    ("real_estate", "commodities"): 0.2,
}
TARGET_MODELS = {  # simple educational reference allocations
    "conservative": {"us_equity": 0.21, "intl_equity": 0.09, "bonds": 0.60, "cash": 0.10},
    "moderate": {"us_equity": 0.42, "intl_equity": 0.18, "bonds": 0.35, "cash": 0.05},
    "aggressive": {"us_equity": 0.60, "intl_equity": 0.30, "bonds": 0.10, "cash": 0.00},
}
# Approximate asset-class returns in past market shocks (rounded index figures, for education):
# 2008 = calendar year (S&P 500, MSCI EAFE, U.S. Aggregate bonds, REITs, Bloomberg Commodity);
# 2020 = Feb 19 – Mar 23 crash; 2022 = calendar year, when stocks and bonds fell together.
STRESS_SCENARIOS = {
    "2008 financial crisis": {"us_equity": -0.37, "intl_equity": -0.43, "bonds": 0.05, "real_estate": -0.38,
                              "commodities": -0.36, "cash": 0.02, "other": -0.35},
    "2020 COVID crash": {"us_equity": -0.34, "intl_equity": -0.33, "bonds": 0.0, "real_estate": -0.42,
                         "commodities": -0.20, "cash": 0.0, "other": -0.30},
    "2022 rate shock": {"us_equity": -0.18, "intl_equity": -0.15, "bonds": -0.13, "real_estate": -0.25,
                        "commodities": 0.16, "cash": 0.015, "other": -0.18},
}
SINGLE_LIMIT, SECTOR_LIMIT = 0.20, 0.40
BROAD = {"Broad Market", "International", "Fixed Income"}


def corr(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if "cash" in (a, b):
        return 0.0
    return _CORR.get((a, b), _CORR.get((b, a), 0.5))


def analyze_portfolio(holdings: list[dict], prices: dict[str, float], info: dict[str, dict],
                      cash: float = 0.0, risk_profile: str = "moderate") -> dict:
    positions, unpriced = [], []
    for h in holdings:
        sym = str(h["symbol"]).upper()
        shares = float(h.get("shares", 0))
        price = prices.get(sym)
        if price is None or shares <= 0:
            unpriced.append(sym)
            continue
        meta = info.get(sym, {})
        value = shares * price
        cost = h.get("cost_basis")
        positions.append({
            "symbol": sym, "name": meta.get("name", sym), "shares": shares, "price": round(price, 2),
            "value": value, "asset_class": meta.get("asset_class", "other"), "sector": meta.get("sector", "Other"),
            "cost_basis": cost, "gain": (price - cost) * shares if cost else None,
            "gain_pct": (price / cost - 1) if cost else None,
        })
    invested = sum(p["value"] for p in positions)
    total = invested + max(cash, 0)
    if total <= 0:
        return {"total_value": 0, "positions": [], "unpriced": unpriced, "flags": ["Portfolio is empty."]}

    for p in positions:
        p["weight"] = p["value"] / total
    by_class: dict[str, float] = {}
    by_sector: dict[str, float] = {}
    for p in positions:
        by_class[p["asset_class"]] = by_class.get(p["asset_class"], 0) + p["weight"]
        by_sector[p["sector"]] = by_sector.get(p["sector"], 0) + p["weight"]
    if cash > 0:
        by_class["cash"] = by_class.get("cash", 0) + cash / total
        by_sector["Cash"] = cash / total

    weights = [p["weight"] for p in positions] + ([cash / total] if cash > 0 else [])
    hhi = sum(w * w for w in weights)
    exp_ret = sum(w * CMA[c][0] for c, w in by_class.items())
    var = sum(wa * wb * CMA[a][1] * CMA[b][1] * corr(a, b)
              for a, wa in by_class.items() for b, wb in by_class.items())
    vol = math.sqrt(max(var, 0))

    flags = []
    for p in sorted(positions, key=lambda x: -x["weight"]):
        if p["weight"] > SINGLE_LIMIT and p["sector"] not in BROAD:
            flags.append(f"{p['symbol']} is {p['weight']:.0%} of the portfolio "
                         f"(single-holding concentration above {SINGLE_LIMIT:.0%}).")
    for s, w in by_sector.items():
        if w > SECTOR_LIMIT and s not in BROAD | {"Cash"}:
            flags.append(f"{s} sector is {w:.0%} of the portfolio (above {SECTOR_LIMIT:.0%}).")
    if by_class.get("intl_equity", 0) == 0 and invested > 0:
        flags.append("No international stock exposure.")
    if by_class.get("bonds", 0) == 0 and risk_profile != "aggressive":
        flags.append("No bond allocation for a non-aggressive profile.")

    target = TARGET_MODELS.get(risk_profile, TARGET_MODELS["moderate"])
    drift = {c: round(by_class.get(c, 0) - t, 4) for c, t in target.items()}
    for c, w in by_class.items():
        drift.setdefault(c, round(w, 4))

    # dollars to move per asset class to reach the reference mix (+ add, - trim); skip moves under 1% of value
    rebalance = {c: round((target.get(c, 0) - by_class.get(c, 0)) * total, 2)
                 for c in set(target) | set(by_class) if abs(target.get(c, 0) - by_class.get(c, 0)) >= 0.01}
    stress = [{"scenario": name, "change_pct": round(sum(w * shocks.get(c, shocks["other"]) for c, w in by_class.items()), 4)}
              for name, shocks in STRESS_SCENARIOS.items()]
    for s in stress:
        s["change_value"] = round(s["change_pct"] * total, 2)

    gains = [p["gain"] for p in positions if p["gain"] is not None]
    return {
        "return_to_risk": round((exp_ret - CMA["cash"][0]) / vol, 2) if vol > 0 else None,
        "rebalance": dict(sorted(rebalance.items(), key=lambda kv: kv[1])), "stress_tests": stress,
        "total_value": round(total, 2), "invested_value": round(invested, 2), "cash": round(cash, 2),
        "positions": sorted(positions, key=lambda x: -x["value"]), "unpriced": unpriced,
        "allocation_by_class": {k: round(v, 4) for k, v in sorted(by_class.items(), key=lambda kv: -kv[1])},
        "allocation_by_sector": {k: round(v, 4) for k, v in sorted(by_sector.items(), key=lambda kv: -kv[1])},
        "hhi": round(hhi, 4), "effective_holdings": round(1 / hhi, 1) if hhi else 0,
        "diversification_score": diversification_score(hhi, by_class, by_sector),
        "expected_return": round(exp_ret, 4), "expected_volatility": round(vol, 4),
        "unrealized_gain": round(sum(gains), 2) if gains else None,
        "risk_profile": risk_profile, "target_allocation": target, "drift": drift, "flags": flags,
    }


def diversification_score(hhi: float, by_class: dict, by_sector: dict) -> int:
    """0-100 heuristic: broad funds and multiple asset classes score higher."""
    broad_share = sum(w for s, w in by_sector.items() if s in BROAD)
    holdings_part = min(1.0, (1 / hhi) / 10) if hhi else 0          # ~10 equal holdings = full marks
    effective = max(holdings_part, broad_share)                      # broad funds hold thousands of names
    classes = sum(1 for c, w in by_class.items() if w >= 0.05 and c != "cash")
    class_part = min(1.0, classes / 3)
    top_sector = max((w for s, w in by_sector.items() if s not in BROAD | {"Cash"}), default=0)
    sector_part = 1 - min(1.0, max(0, top_sector - 0.25) / 0.5)
    return round(100 * (0.45 * effective + 0.30 * class_part + 0.25 * sector_part))
