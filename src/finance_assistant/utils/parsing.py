"""Lightweight extraction of tickers, amounts and horizons from free text."""
from __future__ import annotations

import re
from datetime import date

_TICKER = re.compile(r"\$?\b([A-Z]{1,5})\b")
NOT_TICKERS = set("""I A AN AND OR THE IS IT IN ON OF TO FOR AT BY IF MY ME WE US DO VS ETF ETFS IRA IRAS
HSA FAQ USD CEO CFO GDP CPI APR APY FDIC SEC IRS RMD TIPS REIT REITS PMI DTI EPS NAV OK YES NO AI API
ROTH FICO SIPC LLC INC ETC ALL ANY NEW NOW HOW WHY WHAT TAX FED""".split())

_AMOUNT = re.compile(r"\$?\s?(\d[\d,]*(?:\.\d+)?)\s*(k|K|m|M|thousand|million|mil)?\b")
_MULT = {"k": 1e3, "thousand": 1e3, "m": 1e6, "mil": 1e6, "million": 1e6}


def extract_tickers(text: str, known: set[str] | None = None) -> list[str]:
    out = []
    for m in _TICKER.finditer(text):
        sym = m.group(1)
        explicit = m.group(0).startswith("$")
        if sym in NOT_TICKERS and not explicit:
            continue
        if known is not None and sym not in known and not explicit:
            continue
        if sym not in out:
            out.append(sym)
    return out


def _amounts(text: str) -> list[tuple[float, int, int]]:
    found = []
    for m in _AMOUNT.finditer(text):
        raw = m.group(1).replace(",", "")
        if not raw:
            continue
        val = float(raw) * _MULT.get((m.group(2) or "").lower(), 1)
        tail = text[m.end():m.end() + 6].lower()
        if tail.lstrip().startswith(("year", "yr", "%", "percent", "month")) and "$" not in m.group(0):
            continue  # "10 years", "7%" are not money
        if 1900 <= val <= 2100 and "$" not in m.group(0):
            continue  # looks like a calendar year
        found.append((val, m.start(), m.end()))
    return found


def parse_goal(text: str) -> dict:
    low = text.lower()
    out: dict = {}
    years = re.search(r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b(?!\s*old)", low)  # skip ages ("30 years old")
    if years:
        out["years"] = float(years.group(1))
    else:
        by = re.search(r"\bby\s+(20\d\d)\b", low)
        if by:
            out["years"] = max(1, int(by.group(1)) - date.today().year)
    rate = re.search(r"(\d+(?:\.\d+)?)\s*%", low)
    if rate:
        out["rate"] = float(rate.group(1)) / 100
    remaining = []
    for val, s, e in _amounts(text):
        window_after, window_before = low[e:e + 25], low[max(0, s - 30):s]
        if re.search(r"(per|a|each|every|/)\s*month|monthly", window_after):
            out["monthly"] = val
        elif re.search(r"((?<!to )have|saved|already|current|starting|start with)", window_before):  # not "to have $1M"
            out["present"] = val
        else:
            remaining.append(val)
    if remaining:
        out["target"] = max(remaining)
    return out


def parse_holdings(text: str, known: set[str] | None = None) -> list[dict]:
    """Parse '10 AAPL, 5 shares of MSFT, VTI: 20' style holdings."""
    holdings: dict[str, float] = {}
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(?:shares?\s+(?:of\s+)?)?\$?([A-Z]{1,5})\b", text):
        sym = m.group(2)
        if sym not in NOT_TICKERS and (known is None or sym in known):
            holdings[sym] = holdings.get(sym, 0) + float(m.group(1))
    for m in re.finditer(r"\$?([A-Z]{1,5})\s*[:=x]\s*(\d+(?:\.\d+)?)", text):
        sym = m.group(1)
        if sym not in NOT_TICKERS and (known is None or sym in known):
            holdings.setdefault(sym, float(m.group(2)))
    return [{"symbol": s, "shares": q} for s, q in holdings.items()]


def fmt_money(x: float) -> str:
    return f"-${abs(x):,.0f}" if x < 0 else f"${x:,.0f}"
