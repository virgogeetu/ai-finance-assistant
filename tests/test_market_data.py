from finance_assistant.data.cache import TTLCache
from finance_assistant.data.market_data import MarketDataService, ProviderError
from finance_assistant.data.rate_limiter import RateLimiter


def test_rate_limiter_windows():
    now = [0.0]
    rl = RateLimiter(per_minute=2, per_day=3, clock=lambda: now[0])
    assert rl.try_acquire() and rl.try_acquire() and not rl.try_acquire()
    now[0] = 61
    assert rl.try_acquire() and not rl.try_acquire()  # daily budget exhausted
    assert rl.remaining()["day"] == 0


def test_cache_ttl_and_stale(tmp_path):
    c = TTLCache(tmp_path)
    c.set("k", {"v": 1}, ttl=0)
    assert c.get("k") is None
    value, _, fresh = c.get("k", allow_stale=True)
    assert value == {"v": 1} and fresh is False
    c2 = TTLCache(tmp_path)  # disk persistence
    assert c2.get("k", allow_stale=True)[0] == {"v": 1}


def test_sample_provider_quote_and_freshness(settings):
    m = MarketDataService(settings)
    q = m.get_quote("aapl")
    assert q["symbol"] == "AAPL" and q["price"] > 0
    assert q["freshness"]["status"] == "sample"
    assert len(m.get_daily("SPY")["series"]) >= 60


class FlakyProvider:
    name = "flaky"

    def __init__(self):
        self.fail = False

    def quote(self, symbol):
        if self.fail:
            raise ProviderError("down")
        return {"symbol": symbol, "price": 10.0, "change": 0, "change_percent": 0,
                "previous_close": 10.0, "volume": 1, "latest_trading_day": "2026-01-02"}


def test_falls_back_to_stale_cache_when_provider_fails(settings, tmp_path):
    settings_local = type(settings)(**{**settings.__dict__, "cache_dir": tmp_path, "quote_ttl": 0})
    m = MarketDataService(settings_local)
    flaky = FlakyProvider()
    m.providers = [flaky]
    assert m.get_quote("VTI")["freshness"]["status"] == "live"
    flaky.fail = True
    q = m.get_quote("VTI")
    assert q["price"] == 10.0 and q["freshness"]["status"] == "stale"


def test_unknown_symbol_errors_cleanly(settings):
    m = MarketDataService(settings)
    out = m.get_quotes(["NOTREAL"])
    assert "error" in out["NOTREAL"]
