"""Market data service: Alpha Vantage -> yfinance -> offline sample.

Every payload carries a `freshness` block so the UI and agents can tell the
user how current the numbers are:
    status: live | cached | stale | sample
"""
from __future__ import annotations

import json
import logging
import math
import random
import time
from datetime import date, datetime, timedelta, timezone

from ..config import Settings
from .cache import TTLCache
from .rate_limiter import RateLimiter

log = logging.getLogger(__name__)
AV_URL = "https://www.alphavantage.co/query"


class ProviderError(Exception):
    pass


class RateLimited(ProviderError):
    pass


def _freshness(source: str, stored_at: float, status: str) -> dict:
    age = max(0, int(time.time() - stored_at))
    return {"source": source, "status": status, "age_seconds": age,
            "as_of": datetime.fromtimestamp(stored_at, tz=timezone.utc).isoformat(timespec="seconds"),
            "label": freshness_label(status, age)}


def freshness_label(status: str, age: int) -> str:
    if status == "sample":
        return "Sample data (offline demo, not real prices)"
    mins = age // 60
    when = "just now" if mins < 1 else f"{mins} min ago" if mins < 120 else f"{mins // 60} h ago"
    return {"live": f"Live, fetched {when}", "cached": f"Cached, fetched {when}",
            "stale": f"Stale, last updated {when} (provider unavailable)"}.get(status, when)


class AlphaVantageProvider:
    name = "alphavantage"

    def __init__(self, api_key: str, limiter: RateLimiter, timeout: float = 10, retries: int = 1, backoff: float = 1.0):
        self.key, self.limiter, self.timeout = api_key, limiter, timeout
        self.retries, self.backoff = retries, backoff

    def _get(self, **params) -> dict:
        if not self.key:
            raise ProviderError("no Alpha Vantage key")
        if not self.limiter.try_acquire():
            raise RateLimited("local Alpha Vantage budget exhausted")
        import requests
        for attempt in range(self.retries + 1):
            try:
                r = requests.get(AV_URL, params={**params, "apikey": self.key}, timeout=self.timeout)
                r.raise_for_status()
                data = r.json()
                break
            except (requests.ConnectionError, requests.Timeout) as exc:  # transient: retry with backoff
                if attempt == self.retries:
                    raise ProviderError(f"Alpha Vantage unreachable: {exc}") from exc
                time.sleep(self.backoff * 2 ** attempt)
            except Exception as exc:
                raise ProviderError(f"Alpha Vantage request failed: {exc}") from exc
        if "Note" in data or "Information" in data:  # AV signals throttling this way
            raise RateLimited(data.get("Note") or data.get("Information"))
        if "Error Message" in data:
            raise ProviderError(data["Error Message"])
        return data

    def quote(self, symbol: str) -> dict:
        q = self._get(function="GLOBAL_QUOTE", symbol=symbol).get("Global Quote") or {}
        if not q.get("05. price"):
            raise ProviderError(f"no quote for {symbol}")
        return {"symbol": symbol, "price": float(q["05. price"]), "change": float(q["09. change"]),
                "change_percent": float(q["10. change percent"].rstrip("%")),
                "previous_close": float(q["08. previous close"]), "volume": int(q["06. volume"]),
                "latest_trading_day": q["07. latest trading day"]}

    def daily(self, symbol: str) -> list[dict]:
        ts = self._get(function="TIME_SERIES_DAILY", symbol=symbol, outputsize="compact").get("Time Series (Daily)")
        if not ts:
            raise ProviderError(f"no history for {symbol}")
        return [{"date": d, "close": float(v["4. close"])} for d, v in sorted(ts.items())]

    def news(self, tickers: list[str]) -> list[dict]:
        params = {"function": "NEWS_SENTIMENT", "limit": 20, "sort": "LATEST"}
        params.update({"tickers": ",".join(tickers)} if tickers else {"topics": "financial_markets"})
        feed = self._get(**params).get("feed", [])
        return [{"title": f["title"], "url": f["url"], "source": f.get("source", ""),
                 "published": f.get("time_published", ""), "summary": f.get("summary", ""),
                 "sentiment_label": f.get("overall_sentiment_label", "Neutral"),
                 "sentiment_score": float(f.get("overall_sentiment_score", 0))} for f in feed]


class YFinanceProvider:
    name = "yfinance"

    def __init__(self):
        import yfinance  # noqa: F401  (raise early if missing)
        self.yf = yfinance

    def quote(self, symbol: str) -> dict:
        hist = self.yf.Ticker(symbol).history(period="5d")
        if len(hist) < 2:
            raise ProviderError(f"no quote for {symbol}")
        last, prev = float(hist["Close"].iloc[-1]), float(hist["Close"].iloc[-2])
        return {"symbol": symbol, "price": round(last, 2), "change": round(last - prev, 2),
                "change_percent": round((last / prev - 1) * 100, 2), "previous_close": round(prev, 2),
                "volume": int(hist["Volume"].iloc[-1]), "latest_trading_day": str(hist.index[-1].date())}

    def daily(self, symbol: str) -> list[dict]:
        hist = self.yf.Ticker(symbol).history(period="6mo")
        if hist.empty:
            raise ProviderError(f"no history for {symbol}")
        return [{"date": str(i.date()), "close": round(float(c), 2)} for i, c in hist["Close"].items()]

    def news(self, tickers: list[str]) -> list[dict]:
        items = []
        for t in (tickers or ["SPY"])[:3]:
            for n in (self.yf.Ticker(t).news or [])[:6]:
                c = n.get("content", n)
                url = (c.get("canonicalUrl") or {}).get("url") or c.get("link", "")
                items.append({"title": c.get("title", ""), "url": url,
                              "source": (c.get("provider") or {}).get("displayName", c.get("publisher", "")),
                              "published": c.get("pubDate", ""), "summary": c.get("summary", ""),
                              "sentiment_label": "Not scored", "sentiment_score": 0.0})
        return items


class SampleProvider:
    """Deterministic offline data so the app and tests work without network."""
    name = "sample"

    def __init__(self, securities: dict):
        self.sec = securities

    def _series(self, symbol: str, days: int = 120) -> list[dict]:
        base = self.sec.get(symbol, {}).get("ref_price", 100.0)
        rng = random.Random(symbol)
        vol = 0.025 if self.sec.get(symbol, {}).get("asset_class") == "us_equity" else 0.008
        p, out, d = base * 0.92, [], date.today() - timedelta(days=int(days * 1.45))
        while len(out) < days:
            d += timedelta(days=1)
            if d.weekday() >= 5:
                continue
            p *= math.exp(rng.gauss(0.0006, vol))
            out.append({"date": d.isoformat(), "close": round(p, 2)})
        scale = base / out[-1]["close"]  # end exactly at reference price
        return [{"date": r["date"], "close": round(r["close"] * scale, 2)} for r in out]

    def quote(self, symbol: str) -> dict:
        if symbol not in self.sec:
            raise ProviderError(f"unknown symbol {symbol} (sample data covers {len(self.sec)} tickers)")
        s = self._series(symbol)
        last, prev = s[-1]["close"], s[-2]["close"]
        return {"symbol": symbol, "price": last, "change": round(last - prev, 2),
                "change_percent": round((last / prev - 1) * 100, 2), "previous_close": prev,
                "volume": 0, "latest_trading_day": s[-1]["date"]}

    def daily(self, symbol: str) -> list[dict]:
        if symbol not in self.sec:
            raise ProviderError(f"unknown symbol {symbol}")
        return self._series(symbol)

    def news(self, tickers: list[str]) -> list[dict]:
        topic = ", ".join(tickers) if tickers else "the market"
        return [{"title": f"[Sample] Analysts weigh earnings outlook for {topic}", "url": "", "source": "Sample feed",
                 "published": "", "summary": "Offline placeholder headline used for demos.",
                 "sentiment_label": "Neutral", "sentiment_score": 0.02},
                {"title": "[Sample] Bond yields edge higher as investors watch inflation data", "url": "",
                 "source": "Sample feed", "published": "", "summary": "Offline placeholder headline.",
                 "sentiment_label": "Somewhat-Bearish", "sentiment_score": -0.18}]


class MarketDataService:
    OVERVIEW = ["SPY", "QQQ", "DIA", "IWM", "VXUS", "BND", "GLD"]

    def __init__(self, settings: Settings):
        self.settings = settings
        self.securities = {k: v for k, v in json.loads((settings.kb_dir / "securities.json").read_text()).items()
                           if not k.startswith("_")}
        self.cache = TTLCache(settings.cache_dir / "market")
        self.limiter = RateLimiter(settings.av_calls_per_minute, settings.av_calls_per_day)
        self.sample = SampleProvider(self.securities)
        self.providers = self._providers()

    def _providers(self) -> list:
        mode, chain = self.settings.market_data_provider, []
        if mode in ("auto", "alphavantage") and self.settings.alpha_vantage_key:
            chain.append(AlphaVantageProvider(self.settings.alpha_vantage_key, self.limiter))
        if mode in ("auto", "yfinance"):
            try:
                chain.append(YFinanceProvider())
            except ImportError:
                pass
        return chain

    @property
    def is_offline(self) -> bool:
        return not self.providers

    def _fetch(self, kind: str, key_arg, ttl: int, call):
        key = f"{kind}:{key_arg}"
        hit = self.cache.get(key)
        if hit:
            value, stored_at, _ = hit
            return {**value, "freshness": _freshness(value["_source"], stored_at, "cached")}
        errors = []
        for p in self.providers:
            try:
                value = {"payload": call(p), "_source": p.name}
                self.cache.set(key, value, ttl)
                return {**value, "freshness": _freshness(p.name, time.time(), "live")}
            except ProviderError as exc:
                errors.append(f"{p.name}: {exc}")
                log.info("provider %s failed for %s: %s", p.name, key, exc)
            except Exception as exc:  # network/library errors
                errors.append(f"{p.name}: {exc}")
        stale = self.cache.get(key, allow_stale=True)
        if stale:
            value, stored_at, _ = stale
            return {**value, "freshness": _freshness(value["_source"], stored_at, "stale"), "errors": errors}
        try:
            return {"payload": call(self.sample), "_source": "sample",
                    "freshness": _freshness("sample", time.time(), "sample"), "errors": errors}
        except ProviderError as exc:
            raise ProviderError("; ".join(errors + [str(exc)])) from exc

    # public API ------------------------------------------------------------
    def get_quote(self, symbol: str) -> dict:
        symbol = symbol.upper()
        r = self._fetch("quote", symbol, self.settings.quote_ttl, lambda p: p.quote(symbol))
        return {**r["payload"], "name": self.info(symbol).get("name", symbol), "freshness": r["freshness"]}

    def get_daily(self, symbol: str) -> dict:
        symbol = symbol.upper()
        r = self._fetch("daily", symbol, self.settings.daily_ttl, lambda p: p.daily(symbol))
        return {"symbol": symbol, "series": r["payload"], "freshness": r["freshness"]}

    def get_news(self, tickers: list[str] | None = None) -> dict:
        tickers = sorted({t.upper() for t in (tickers or [])})
        r = self._fetch("news", ",".join(tickers) or "market", self.settings.news_ttl, lambda p: p.news(tickers))
        return {"tickers": tickers, "articles": r["payload"], "freshness": r["freshness"]}

    def get_quotes(self, symbols: list[str]) -> dict[str, dict]:
        out = {}
        for s in symbols:
            try:
                out[s.upper()] = self.get_quote(s)
            except ProviderError as exc:
                out[s.upper()] = {"symbol": s.upper(), "error": str(exc)}
        return out

    def market_overview(self) -> dict[str, dict]:
        return self.get_quotes(self.OVERVIEW)

    def info(self, symbol: str) -> dict:
        return self.securities.get(symbol.upper(), {})

    def known_symbol(self, symbol: str) -> bool:
        return symbol.upper() in self.securities

    def status(self) -> dict:
        return {"providers": [p.name for p in self.providers] or ["sample"],
                "alpha_vantage_budget": self.limiter.remaining()}
