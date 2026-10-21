"""LangGraph orchestration.

    router ──► agent_1 ──► agent_2 ──► … ──► compose ──► END
                 ▲  (conditional edges pick the next pending agent;
                 └── agents may add hand-offs; failures add a QA fallback)

If LangGraph is not installed, the same node functions run in a small
built-in loop so the app, tests and MCP server still work.
"""
from __future__ import annotations

import logging
from copy import deepcopy

from .. import DISCLAIMER
from ..agents import ALL_AGENTS
from ..config import Settings, get_settings
from ..core.guardrails import UsageGuard, Verdict, check_question, redact_pii
from ..core.llm import LLMClient
from ..core.state import FinanceState
from ..data.market_data import MarketDataService
from ..rag.retriever import Retriever
from .followups import suggest
from .router import Router

log = logging.getLogger(__name__)
FALLBACK_AGENT = "finance_qa"

try:
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, StateGraph
    HAS_LANGGRAPH = True
except ImportError:  # pragma: no cover
    HAS_LANGGRAPH = False


class FinanceWorkflow:
    def __init__(self, settings: Settings | None = None, llm=None, retriever=None, market=None):
        self.settings = settings or get_settings()
        self.llm = llm or LLMClient(self.settings)
        self.retriever = retriever or Retriever(self.settings)
        self.market = market or MarketDataService(self.settings)
        self.agents = {cls.name: cls(self.llm, self.retriever, self.market, self.settings) for cls in ALL_AGENTS}
        self.router = Router(self.llm, set(self.market.securities))
        self.usage = UsageGuard(self.settings.questions_per_minute, self.settings.questions_per_hour,
                                self.settings.site_questions_per_day)
        self._threads: dict[str, dict] = {}  # used only without LangGraph
        self.graph = self._build_graph() if HAS_LANGGRAPH else None

    @property
    def engine(self) -> str:
        return "langgraph" if self.graph is not None else "builtin"

    # ------------------------------------------------------------------ nodes
    def route_node(self, state: FinanceState) -> dict:
        ctx = dict(state.get("context") or {})
        if state.get("documents"):  # routing hint only; not saved to context
            ctx["attached_files"] = [d["name"] for d in state["documents"]]
        route, reason = self.router.route(state["query"], ctx)
        return {"route": route, "route_reason": reason, "pending": list(route), "completed": [],
                "results": [], "final_response": "", "sources": []}

    def make_agent_node(self, name: str):
        agent = self.agents[name]

        def node(state: FinanceState) -> dict:
            pending = [p for p in state.get("pending", []) if p != name]
            completed = list(state.get("completed", [])) + [name]
            res = agent.run(state)
            budget = self.settings.max_agents_per_turn
            for h in res.get("handoffs", []):
                if h in self.agents and h not in completed + pending and len(completed) + len(pending) < budget:
                    pending.append(h)
            if res.get("error") and name != FALLBACK_AGENT and FALLBACK_AGENT not in completed + pending:
                pending.append(FALLBACK_AGENT)  # graceful degradation
            ctx = dict(state.get("context") or {})
            data = res.get("data") or {}
            if data.get("tickers"):
                ctx["last_tickers"] = data["tickers"]
            if data.get("goal"):
                ctx["last_goal"] = data["goal"]
            return {"pending": pending, "completed": completed, "context": ctx,
                    "results": list(state.get("results", [])) + [res]}

        return node

    @staticmethod
    def next_step(state: FinanceState) -> str:
        pending = state.get("pending") or []
        return pending[0] if pending else "compose"

    def compose_node(self, state: FinanceState) -> dict:
        ok = [r for r in state.get("results", []) if not r.get("error") and r.get("content")]
        answered = [r for r in ok if not (r.get("data") or {}).get("needs_input")]
        if answered and len(answered) < len(ok):
            ok = answered  # skip "I need your holdings…" when another agent already answered
        if not ok:
            text = ("Sorry, I ran into a problem answering that. Please try rephrasing, or ask about a specific "
                    "concept such as ETFs, budgeting, or retirement accounts.")
        elif len(ok) == 1:
            text = ok[0]["content"]
        else:
            text = "\n\n".join(f"### {r['title']}\n{r['content']}" for r in ok)
        sources, seen = [], set()
        for r in ok:
            for s in r.get("sources", []):
                key = (s.get("title"), s.get("url") or "")
                if key not in seen:
                    seen.add(key)
                    sources.append(s)
        final = f"{text}\n\n{DISCLAIMER}"
        ctx = dict(state.get("context") or {})
        ctx["last_agents"] = [r["agent"] for r in ok]
        hints = {**ctx, "has_files": bool(state.get("turn_files"))}
        return {"final_response": final, "sources": sources, "context": ctx,
                "suggestions": suggest(ok, hints, state.get("query", "")),
                "messages": [{"role": "assistant", "content": text}]}

    # ------------------------------------------------------------ build / run
    def _targets(self) -> dict[str, str]:
        return {**{n: n for n in self.agents}, "compose": "compose"}

    def _build_graph(self):
        g = StateGraph(FinanceState)
        g.add_node("router", self.route_node)
        for name in self.agents:
            g.add_node(name, self.make_agent_node(name))
        g.add_node("compose", self.compose_node)
        g.set_entry_point("router")
        g.add_conditional_edges("router", self.next_step, self._targets())
        for name in self.agents:
            g.add_conditional_edges(name, self.next_step, self._targets())
        g.add_edge("compose", END)
        return g.compile(checkpointer=MemorySaver())

    def _run_builtin(self, inputs: dict, thread_id: str) -> dict:
        state = deepcopy(self._threads.get(thread_id, {"messages": [], "context": {}}))

        def apply(update: dict):
            for k, v in update.items():
                state[k] = state.get(k, []) + v if k in ("messages", "documents") else v

        apply(inputs)
        apply(self.route_node(state))
        for _ in range(10):  # recursion guard
            step = self.next_step(state)
            if step == "compose":
                break
            apply(self.make_agent_node(step)(state))
        apply(self.compose_node(state))
        self._threads[thread_id] = state
        return state

    def check(self, query: str, visitor: str | None = None) -> Verdict:
        """Misuse/injection/length checks, then (if `visitor` is given) usage limits, which count this question.
        The UI calls this before reading files or audio, then calls chat() with visitor=None."""
        verdict = check_question(query, self.settings.max_question_chars)
        if verdict.allowed and visitor is not None:
            verdict = self.usage.check(visitor)
        return verdict

    def chat(self, query: str, thread_id: str = "default", portfolio: dict | None = None,
             user_profile: dict | None = None, attachments: list[dict] | None = None,
             visitor: str | None = None) -> dict:
        """`attachments`: documents from `core.attachments.read_file`; they stay with the thread.
        `visitor`: an id (e.g. IP or session) for per-visitor usage limits; None skips them (CLI, tests)."""
        # guardrails run before anything is stored or sent to an AI provider
        verdict = self.check(query, visitor)
        if not verdict.allowed:
            log.info("guardrail blocked a question: %s", verdict.reason)
            return {"response": verdict.message, "agents": [], "sources": [], "results": [],
                    "route_reason": f"guardrail: {verdict.reason}", "suggestions": [], "blocked": verdict.reason}
        query, removed = redact_pii(query)
        if attachments:
            attachments = [dict(d) for d in attachments]
            for d in attachments:
                d["text"], found = redact_pii(d.get("text", ""))
                removed += found
        removed = sorted(set(removed))
        content = query
        if attachments:
            content += "\n(attached: " + ", ".join(d["name"] for d in attachments) + ")"
        inputs: dict = {"query": query, "messages": [{"role": "user", "content": content}],
                        "turn_files": [d["name"] for d in attachments or []]}
        if attachments:
            inputs["documents"] = attachments
        if portfolio is not None:
            inputs["portfolio"] = portfolio
        if user_profile is not None:
            inputs["user_profile"] = user_profile
        try:
            if self.graph is not None:
                out = self.graph.invoke(inputs, config={"configurable": {"thread_id": thread_id},
                                                        "recursion_limit": 25})
            else:
                out = self._run_builtin(inputs, thread_id)
        except Exception as exc:  # last-resort fallback
            log.exception("workflow failed")
            return {"response": f"Something went wrong while processing your request ({type(exc).__name__}). "
                                f"Please try again.\n\n{DISCLAIMER}", "agents": [], "sources": [], "results": [],
                    "route_reason": "error", "suggestions": []}
        response = out["final_response"]
        if removed:
            response = (f"🔒 For your privacy I removed the {', '.join(removed)} from your message before processing it. "
                        f"Please don't share details like these here.\n\n{response}")
        return {"response": response, "agents": out.get("completed", []),
                "route_reason": out.get("route_reason", ""), "sources": out.get("sources", []),
                "results": out.get("results", []), "suggestions": out.get("suggestions", []), "redacted": removed}

    def history(self, thread_id: str = "default") -> list[dict]:
        if self.graph is not None:
            snap = self.graph.get_state({"configurable": {"thread_id": thread_id}})
            return (snap.values or {}).get("messages", [])
        return self._threads.get(thread_id, {}).get("messages", [])
