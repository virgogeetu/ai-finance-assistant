"""Shared workflow state and the agent communication protocol.

Agents never call each other directly. They read from and write to a shared
state object (a *blackboard*), and return a typed `AgentResult` envelope. An
agent can ask the orchestrator to run another agent next by listing it in
`handoffs`; the orchestrator de-duplicates and caps hops.
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class Source(TypedDict, total=False):
    title: str
    category: str
    url: str
    score: float
    kind: str            # "kb" | "glossary" | "market" | "news"


class AgentResult(TypedDict, total=False):
    agent: str
    title: str           # heading used when several agents answer
    content: str         # user-facing markdown
    sources: list[Source]
    data: dict[str, Any] # structured output for the UI (charts, tables)
    confidence: float    # 0..1, used by compose step
    handoffs: list[str]  # agents this agent wants to run next
    error: str | None


class FinanceState(TypedDict, total=False):
    # persistent across turns (checkpointed per thread)
    messages: Annotated[list[dict], operator.add]   # {"role": "user"|"assistant", "content": str}
    user_profile: dict[str, Any]                    # risk_profile, age, horizon...
    portfolio: dict[str, Any] | None                # {"holdings": [...], "cash": float}
    context: dict[str, Any]                         # last_tickers, last_agents, last_goal
    documents: Annotated[list[dict], operator.add]  # uploaded files: {"name", "kind", "text", "note"}

    # per-turn
    query: str
    turn_files: list[str]                           # names of files attached with this question
    route: list[str]
    route_reason: str
    pending: list[str]
    completed: list[str]
    results: list[AgentResult]
    final_response: str
    suggestions: list[str]                          # follow-up questions for the UI
    sources: list[Source]
