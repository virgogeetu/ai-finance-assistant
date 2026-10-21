"""Price-trend metrics from a daily close series (pure functions, no I/O).

Used by the market agent, the Markets tab and the MCP server to turn raw prices
into beginner-friendly context: recent returns, moving averages, volatility and
drawdown, each with a one-line plain-English reading. Descriptive, not a forecast.
"""
from __future__ import annotations

import math
import statistics

TRADING_DAYS = 252
TREND_WORDS = {"uptrend": "an **uptrend** (price and 20-day average above the 50-day)",
               "downtrend": "a **downtrend** (price and 20-day average below the 50-day)",
               "mixed": "**mixed**, with no clear direction"}


def _ret(closes: list[float], days: int) -> float | None:
    return closes[-1] / closes[-1 - days] - 1 if len(closes) > days else None


def _sma(closes: list[float], days: int) -> float | None:
    return sum(closes[-days:]) / days if len(closes) >= days else None


def max_drawdown(closes: list[float]) -> float:
    """Largest peak-to-trough fall, as a negative fraction (0 if prices never fell)."""
    peak, worst = closes[0], 0.0
    for c in closes:
        peak = max(peak, c)
        worst = min(worst, c / peak - 1)
    return worst


def annual_volatility(closes: list[float]) -> float | None:
    rets = [math.log(b / a) for a, b in zip(closes, closes[1:], strict=False) if a > 0 and b > 0]
    return statistics.stdev(rets) * math.sqrt(TRADING_DAYS) if len(rets) >= 2 else None


def trend_metrics(series: list[dict]) -> dict:
    closes = [float(r["close"]) for r in series if r.get("close") is not None]
    if len(closes) < 2:
        return {"points": len(closes), "summary": ["Not enough price history to describe a trend."]}
    last, sma20, sma50 = closes[-1], _sma(closes, 20), _sma(closes, 50)
    vol, dd = annual_volatility(closes), max_drawdown(closes)
    out = {
        "points": len(closes), "start_date": series[0]["date"], "end_date": series[-1]["date"],
        "last": round(last, 2), "period_high": round(max(closes), 2), "period_low": round(min(closes), 2),
        "return_1m": _ret(closes, 21), "return_3m": _ret(closes, 63), "return_period": closes[-1] / closes[0] - 1,
        "sma_20": sma20, "sma_50": sma50, "vs_sma_50": (last / sma50 - 1) if sma50 else None,
        "annual_volatility": vol, "max_drawdown": dd,
    }
    if sma20 and sma50:
        out["trend"] = ("uptrend" if last > sma50 and sma20 > sma50 else
                        "downtrend" if last < sma50 and sma20 < sma50 else "mixed")
    else:
        out["trend"] = "mixed"
    if vol is not None:
        out["volatility_level"] = "low" if vol < 0.15 else "moderate" if vol < 0.30 else "high"
    out["summary"] = _explain(out)
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in out.items()}


def _explain(m: dict) -> list[str]:
    lines = []
    if m["return_3m"] is not None:
        lines.append(f"Over about 3 months the price moved {m['return_3m']:+.1%}"
                     + (f" ({m['return_1m']:+.1%} in the last month)." if m["return_1m"] is not None else "."))
    elif m["return_1m"] is not None:
        lines.append(f"Over about a month the price moved {m['return_1m']:+.1%}.")
    if m["vs_sma_50"] is not None:
        side = "above" if m["vs_sma_50"] >= 0 else "below"
        lines.append(f"It trades {abs(m['vs_sma_50']):.1%} {side} its 50-day average, a common way to smooth out "
                     f"daily noise. The recent pattern is {TREND_WORDS[m['trend']]}.")
    if m.get("annual_volatility") is not None:
        lines.append(f"Annualized volatility is about {m['annual_volatility']:.0%} ({m['volatility_level']}): "
                     "a rough gauge of how bumpy the ride has been.")
    if m["max_drawdown"] < -0.05:
        lines.append(f"The biggest drop from a high in this window was {m['max_drawdown']:.0%}.")
    lines.append("Past moves describe what happened; they don't predict what comes next.")
    return lines
