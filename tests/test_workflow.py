import json

from finance_assistant import DISCLAIMER
from finance_assistant.workflow.router import Router


def route(q, ctx=None):
    return Router(known_tickers={"AAPL", "VTI", "NVDA"}).keyword_route(q, ctx)[0]


def test_router_intents():
    assert route("What is compound interest?") == ["finance_qa"]
    assert route("Can you review my portfolio?")[0] == "portfolio_analysis"
    assert route("How is AAPL doing today?")[0] == "market_analysis"
    assert route("How much should I save for a down payment in 5 years?")[0] == "goal_planning"
    assert route("How are capital gains taxed?")[0] == "tax_education"
    assert "news_synthesizer" in route("Any news on NVDA this week?")
    assert route("hello") == ["finance_qa"]


def test_end_to_end_answers_have_disclaimer_and_sources(workflow):
    r = workflow.chat("What is an expense ratio?", thread_id="t-e2e")
    assert r["agents"] == ["finance_qa"]
    assert DISCLAIMER in r["response"] and r["sources"]


def test_portfolio_flow_and_context(workflow, settings):
    pf = json.loads((settings.kb_dir / "sample_portfolios.json").read_text())["tech_heavy"]
    r = workflow.chat("Please analyze my portfolio", thread_id="t-pf", portfolio=pf)
    analysis = r["results"][0]["data"]["analysis"]
    assert analysis["total_value"] > 0 and analysis["flags"]
    # follow-up in the same thread keeps memory
    workflow.chat("What is diversification?", thread_id="t-pf")
    assert len(workflow.history("t-pf")) == 4


def test_handoff_market_to_news(workflow):
    r = workflow.chat("Why is NVDA down today?", thread_id="t-ho")
    assert "market_analysis" in r["agents"] and "news_synthesizer" in r["agents"]


def test_failing_agent_falls_back_to_qa(workflow):
    agent = workflow.agents["goal_planning"]
    original = agent._run
    agent._run = lambda state: (_ for _ in ()).throw(RuntimeError("boom"))
    try:
        r = workflow.chat("How much should I save monthly for $20k in 5 years?", thread_id="t-fb")
    finally:
        agent._run = original
    assert "finance_qa" in r["agents"]
    assert any(res.get("error") for res in r["results"])
    assert r["response"].strip()


def test_goal_agent_asks_for_missing_info(workflow):
    r = workflow.chat("Help me plan a savings goal", thread_id="t-goal")
    goal = [x for x in r["results"] if x["agent"] == "goal_planning"][0]
    assert goal["data"].get("needs_input")


def test_unpriceable_portfolio_does_not_crash(workflow):
    r = workflow.chat("review my portfolio", thread_id="t-unpriced",
                      portfolio={"holdings": [{"symbol": "ZZZZ", "shares": 5}], "cash": 0})
    res = r["results"][0]
    assert res["agent"] == "portfolio_analysis" and not res["error"] and "ZZZZ" in res["content"]


def test_compose_skips_agents_that_only_ask_for_input(workflow):
    out = workflow.compose_node({"results": [
        {"agent": "portfolio_analysis", "title": "Portfolio review", "content": "I need your holdings.",
         "data": {"needs_input": "portfolio"}},
        {"agent": "finance_qa", "title": "Financial concepts", "content": "APY means annual percentage yield."}]})
    assert "holdings" not in out["final_response"] and "APY means" in out["final_response"]
    assert out["context"]["last_agents"] == ["finance_qa"]
