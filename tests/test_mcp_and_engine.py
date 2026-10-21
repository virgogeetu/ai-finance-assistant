"""MCP server tools, the built-in (no-LangGraph) engine, error paths and the NumPy vector store."""
import asyncio
import importlib
import json
import sys

import numpy as np
import pytest

from finance_assistant.rag import vector_store
from finance_assistant.rag.chunker import Chunk
from finance_assistant.workflow import graph


@pytest.fixture(scope="module")
def server(workflow, settings):
    sys.path.insert(0, str(settings.kb_dir.parent / "mcp_server"))
    mod = importlib.import_module("server")
    mod._wf = workflow  # reuse the offline test workflow
    return mod


def test_mcp_lists_all_tools(server):
    names = {t.name for t in asyncio.run(server.mcp.list_tools())}
    assert names == {"ask_finance_assistant", "search_knowledge_base", "get_stock_quote", "analyze_holdings",
                     "project_savings_goal", "get_market_overview", "get_price_trend", "get_financial_news"}


def test_mcp_tools_return_json_and_text(server):
    assert "Educational information only" in server.ask_finance_assistant("What is an index fund?")
    hits = json.loads(server.search_knowledge_base("expense ratio", k=2))
    assert hits and {"title", "score", "text"} <= hits[0].keys()
    assert json.loads(server.get_stock_quote("vti"))["freshness"]["status"] == "sample"
    a = json.loads(server.analyze_holdings('[{"symbol": "VTI", "shares": 10}, {"symbol": "BND", "shares": 5}]', 100))
    assert a["total_value"] > 0 and a["stress_tests"]
    plan = json.loads(server.project_savings_goal(50_000, 10, 5_000, 300))
    assert "schedule" not in plan and "bands" not in plan["monte_carlo"]
    assert "SPY" in json.loads(server.get_market_overview())
    assert json.loads(server.get_price_trend("SPY"))["points"] > 50
    assert json.loads(server.get_financial_news("AAPL, MSFT"))["articles"]
    assert "Expense Ratio" in json.loads(server.glossary())


def test_mcp_wf_builds_workflow_lazily(server, monkeypatch):
    monkeypatch.setattr(server, "_wf", None)
    monkeypatch.setattr(server, "FinanceWorkflow", lambda: "built")
    assert server.wf() == "built"


@pytest.fixture
def builtin(settings, monkeypatch):
    monkeypatch.setattr(graph, "HAS_LANGGRAPH", False)
    return graph.FinanceWorkflow(settings)


def test_builtin_engine_runs_the_same_flow_with_memory(builtin):
    assert builtin.engine == "builtin"
    r = builtin.chat("Why is NVDA down today?", thread_id="b1")
    assert r["agents"][:2] == ["market_analysis", "news_synthesizer"] and r["suggestions"]
    builtin.chat("What is an ETF?", thread_id="b1",
                 attachments=[{"name": "n.txt", "kind": "txt", "text": "ETF notes", "note": ""}])
    hist = builtin.history("b1")
    assert len(hist) == 4 and hist[2]["content"].endswith("(attached: n.txt)")
    assert builtin.history("nope") == []


def test_workflow_survives_router_crash_and_all_agents_failing(builtin, monkeypatch):
    monkeypatch.setattr(builtin.router, "route", lambda q, c: (_ for _ in ()).throw(RuntimeError("boom")))
    r = builtin.chat("anything", thread_id="b2")
    assert "Something went wrong" in r["response"] and r["route_reason"] == "error"
    out = builtin.compose_node({"results": [{"agent": "x", "error": "fail", "content": ""}]})
    assert out["final_response"].startswith("Sorry, I ran into a problem")


def test_numpy_vector_store_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(vector_store, "faiss", None)
    s = vector_store.FaissStore(2)
    assert s.backend == "numpy" and s.search(np.array([1.0, 0.0]), 3) == []
    chunks = [Chunk(id=f"c{i}", doc_id=f"d{i}", title=f"T{i}", category="basics", text=f"t{i}") for i in range(2)]
    s.add(np.array([[1.0, 0.0], [0.0, 1.0]]), chunks)
    assert s.search(np.array([0.0, 1.0]), 5)[0][1].id == "c1"
    s.save(tmp_path)
    loaded = vector_store.FaissStore.load(tmp_path)
    assert loaded.backend == "numpy" and len(loaded.chunks) == 2
    assert vector_store.FaissStore.load(tmp_path / "missing") is None
