"""Market-data providers with the network replaced by fakes (no real API calls)."""
import types

import pytest
import requests

from finance_assistant.data import market_data as md
from finance_assistant.data.market_data import (AlphaVantageProvider, MarketDataService, ProviderError, RateLimited,
                                                YFinanceProvider, freshness_label)
from finance_assistant.data.rate_limiter import RateLimiter

AV_QUOTE = {"Global Quote": {"05. price": "101.50", "09. change": "1.50", "10. change percent": "1.5%",
                             "08. previous close": "100.00", "06. volume": "12345", "07. latest trading day": "2026-10-16"}}
AV_DAILY = {"Time Series (Daily)": {"2026-10-16": {"4. close": "101.5"}, "2026-10-15": {"4. close": "100.0"}}}
AV_NEWS = {"feed": [{"title": "Fed holds rates", "url": "https://x", "source": "Wire", "time_published": "20261016",
                     "summary": "s", "overall_sentiment_label": "Neutral", "overall_sentiment_score": "0.05"}]}


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload, self.status_code = payload, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


def fake_get(responses):
    """requests.get replacement that returns (or raises) queued items in order."""
    calls = []

    def get(url, params=None, timeout=None):
        calls.append(params)
        item = responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item
    return get, calls


def av(**kw):
    return AlphaVantageProvider("demo-key", RateLimiter(100, 100), backoff=0, **kw)


def test_alpha_vantage_parses_quote_daily_and_news(monkeypatch):
    get, calls = fake_get([FakeResponse(AV_QUOTE), FakeResponse(AV_DAILY), FakeResponse(AV_NEWS), FakeResponse(AV_NEWS)])
    monkeypatch.setattr(requests, "get", get)
    p = av()
    q = p.quote("AAPL")
    assert q["price"] == 101.5 and q["change_percent"] == 1.5 and q["volume"] == 12345
    assert [r["date"] for r in p.daily("AAPL")] == ["2026-10-15", "2026-10-16"]  # sorted oldest first
    assert p.news(["AAPL"])[0]["sentiment_score"] == 0.05
    p.news([])
    assert calls[2]["tickers"] == "AAPL" and calls[3]["topics"] == "financial_markets"


@pytest.mark.parametrize("payload, error", [
    ({"Note": "Thank you for using Alpha Vantage! 5 calls per minute"}, RateLimited),
    ({"Information": "premium endpoint"}, RateLimited),
    ({"Error Message": "Invalid API call"}, ProviderError),
    ({"Global Quote": {}}, ProviderError),
])
def test_alpha_vantage_error_payloads(monkeypatch, payload, error):
    monkeypatch.setattr(requests, "get", fake_get([FakeResponse(payload)])[0])
    with pytest.raises(error):
        av().quote("AAPL")


def test_alpha_vantage_retries_transient_errors_then_succeeds(monkeypatch):
    get, calls = fake_get([requests.ConnectionError("reset"), FakeResponse(AV_QUOTE)])
    monkeypatch.setattr(requests, "get", get)
    assert av(retries=1).quote("MSFT")["price"] == 101.5 and len(calls) == 2


def test_alpha_vantage_gives_up_after_retries_and_on_http_errors(monkeypatch):
    monkeypatch.setattr(requests, "get", fake_get([requests.Timeout("slow"), requests.Timeout("slow")])[0])
    with pytest.raises(ProviderError, match="unreachable"):
        av(retries=1).quote("MSFT")
    monkeypatch.setattr(requests, "get", fake_get([FakeResponse({}, status=503)])[0])
    with pytest.raises(ProviderError, match="request failed"):
        av().quote("MSFT")


def test_alpha_vantage_needs_key_and_respects_local_budget():
    with pytest.raises(ProviderError, match="no Alpha Vantage key"):
        AlphaVantageProvider("", RateLimiter(5, 25)).quote("AAPL")
    with pytest.raises(RateLimited):
        AlphaVantageProvider("k", RateLimiter(0, 0)).quote("AAPL")


class FakeFrame:
    """Just enough of a pandas DataFrame for YFinanceProvider."""

    def __init__(self, closes, dates):
        import pandas as pd
        idx = pd.to_datetime(dates)
        self._df = pd.DataFrame({"Close": closes, "Volume": [1000] * len(closes)}, index=idx)

    def __len__(self):
        return len(self._df)

    def __getitem__(self, k):
        return self._df[k]

    @property
    def index(self):
        return self._df.index

    @property
    def empty(self):
        return self._df.empty


def fake_yfinance(closes, news=None):
    dates = [f"2026-10-{d:02d}" for d in range(1, len(closes) + 1)]

    class Ticker:
        def __init__(self, sym):
            self.news = news or []

        def history(self, period):
            return FakeFrame(closes, dates)
    return types.SimpleNamespace(Ticker=Ticker)


def test_yfinance_provider_with_fake_library():
    p = YFinanceProvider.__new__(YFinanceProvider)
    p.yf = fake_yfinance([100.0, 102.0], news=[{"content": {"title": "Chip demand", "canonicalUrl": {"url": "u"},
                                                            "provider": {"displayName": "Yahoo"}}}])
    q = p.quote("NVDA")
    assert q["price"] == 102.0 and q["change_percent"] == 2.0 and q["latest_trading_day"] == "2026-10-02"
    assert p.daily("NVDA")[-1] == {"date": "2026-10-02", "close": 102.0}
    n = p.news(["NVDA"])[0]
    assert n["title"] == "Chip demand" and n["source"] == "Yahoo" and n["sentiment_label"] == "Not scored"
    p.yf = fake_yfinance([100.0])
    with pytest.raises(ProviderError):
        p.quote("NVDA")
    p.yf = fake_yfinance([])
    with pytest.raises(ProviderError):
        p.daily("NVDA")


def test_provider_chain_follows_settings(settings, monkeypatch):
    monkeypatch.setattr(md, "YFinanceProvider", lambda: types.SimpleNamespace(name="yfinance"))
    s = type(settings)(**{**settings.__dict__, "market_data_provider": "auto", "alpha_vantage_key": "k"})
    assert [p.name for p in MarketDataService(s).providers] == ["alphavantage", "yfinance"]
    s.market_data_provider = "sample"
    m = MarketDataService(s)
    assert m.providers == [] and m.is_offline and m.status()["providers"] == ["sample"]


def test_generic_provider_exceptions_fall_back_to_sample(settings, tmp_path):
    s = type(settings)(**{**settings.__dict__, "cache_dir": tmp_path})
    m = MarketDataService(s)

    class Broken:
        name = "broken"

        def quote(self, symbol):
            raise RuntimeError("socket closed")
    m.providers = [Broken()]
    q = m.get_quote("SPY")
    assert q["freshness"]["status"] == "sample" and m.known_symbol("spy") and not m.known_symbol("ZZZZ")
    with pytest.raises(ProviderError, match="broken"):
        m.get_daily("ZZZZ")  # no provider, no cache, not in sample set


def test_freshness_labels():
    assert freshness_label("live", 30) == "Live, fetched just now"
    assert freshness_label("cached", 600) == "Cached, fetched 10 min ago"
    assert freshness_label("stale", 3 * 3600).startswith("Stale, last updated 3 h ago")
    assert freshness_label("other", 0) == "just now"
