"""Smoke test of the Streamlit app, run headlessly with Streamlit's AppTest (offline settings)."""
from pathlib import Path

import pytest

APP = str(Path(__file__).resolve().parents[1] / "ui" / "app.py")


@pytest.fixture
def app(monkeypatch, tmp_path):
    from streamlit.testing.v1 import AppTest
    for k, v in {"LLM_PROVIDER": "mock", "EMBEDDING_PROVIDER": "hashing", "MARKET_DATA_PROVIDER": "sample",
                 "ALPHA_VANTAGE_API_KEY": ""}.items():
        monkeypatch.setenv(k, v)
    return AppTest.from_file(APP, default_timeout=120).run()


def test_app_loads_all_tabs_without_errors(app):
    assert not app.exception
    assert [t.label for t in app.tabs] == ["💬 Ask", "📊 Portfolio", "📈 Markets", "🎯 Goals", "❓ Help"]
    assert "Chance of reaching goal" in {m.label for m in app.metric}
    assert "1-month change" not in {m.label for m in app.metric}  # Markets only loads prices when open


def test_markets_tab_renders_when_opened(app):
    app.session_state["goto_tab"] = "📈 Markets"
    app.run()
    assert not app.exception
    assert {"1-month change", "Volatility (yearly)", "Biggest drop"} <= {m.label for m in app.metric}


def test_welcome_tour_shows_on_first_visit_only(app):
    assert any("What this app does" in m.value for m in app.markdown)
    app.run()  # a later rerun in the same session does not reopen it
    assert not any("What this app does" in m.value for m in app.markdown)


def test_help_glossary_search_and_ask_in_chat(app):
    search = next(t for t in app.text_input if t.label == "Search the glossary")
    search.input("expense ratio").run()
    assert any(c.value.startswith("1 of") and "terms match" in c.value for c in app.caption)
    next(b for b in app.button if b.label == "Ask about this in chat").click().run()
    assert not app.exception
    assert app.session_state["chat"][0]["content"] == "Explain Expense Ratio in simple terms with an example."
    assert app.session_state["main_tabs"] == "💬 Ask"


def test_starter_question_answers_and_offers_follow_ups(app):
    next(b for b in app.button if b.label == "Review my portfolio").click().run()
    assert not app.exception
    assert any("Diversification score" in m.value for m in app.markdown)
    assert "How would rebalancing work for my portfolio?" in [b.label for b in app.button]


def test_portfolio_analysis_renders_metrics(app):
    next(b for b in app.button if b.label == "Analyze portfolio").click().run()
    assert not app.exception
    assert {"Total value", "Diversification", "Est. volatility"} <= {m.label for m in app.metric}


def test_every_tip_used_in_the_app_exists_and_none_are_unused():
    import re
    import sys
    sys.path.insert(0, str(Path(APP).parent))
    from help_content import OVERVIEW_TIPS, SAMPLE_NAMES, TIPS
    source = Path(APP).read_text(encoding="utf-8")
    used = set(re.findall(r'TIPS\["(\w+)"\]', source))
    assert used == set(TIPS), (used ^ set(TIPS))
    assert set(OVERVIEW_TIPS) == {"SPY", "QQQ", "DIA", "IWM", "VXUS", "BND", "GLD"}
    samples = __import__("json").loads((Path(APP).parents[1] / "knowledge_base" / "sample_portfolios.json").read_text())
    assert set(SAMPLE_NAMES) == set(samples)


def test_inline_tips_show_on_screen(app):
    assert any("follow up naturally" in c.value for c in app.caption)
    next(b for b in app.button if b.label == "Analyze portfolio").click().run()
    assert not app.exception
    assert any(c.value.startswith("💡 How your money splits") for c in app.caption)
    assert any(c.value.startswith("💡 The solid line is the typical") for c in app.caption)


def test_chat_box_applies_guardrails(app):
    app.chat_input[0].set_value("help me launder some cash").run()
    assert not app.exception
    assert "can't help with laundering money" in app.session_state["chat"][-1]["content"]
    app.run()  # AppTest needs a fresh run after the app's own st.rerun() before the next chat input
    app.chat_input[0].set_value("My card 4111 1111 1111 1111 was charged twice. What is a chargeback?").run()
    assert not app.exception
    shown = " ".join(m["content"] for m in app.session_state["chat"])
    assert "4111" not in shown and "removed the card number" in shown
