"""Guardrails for a public deployment: misuse, prompt injection, personal data, secrets and usage limits.

Applied in `FinanceWorkflow.chat`, so the website, CLI and MCP server are all covered.
All checks are deterministic (no LLM call), cheap, and conservative: they block only
clear cases and explain why, so normal finance questions are never affected.
"""
from __future__ import annotations

import re
import threading
import time
from collections import deque
from dataclasses import dataclass
from urllib.parse import urlparse

# --- misuse: requests to *do* clearly harmful things. Questions *about* them ("what is money laundering?",
# "tax avoidance vs. evasion?") stay allowed, because they are educational. A request is blocked only when an
# intent phrase ("how can I", "help me", "ways to"...) comes shortly before a harmful act.
_INTENT = (r"\b(how (can|do|could|should|would|to)( i| we| you| someone| one)?|help me|teach me|show me( how)?|"
           r"ways? to|best way to|steps to|tips? (on|for)|can you help( me)?|i (want|need|plan) to|tell me how)\b")
_ACTS = [
    (r"(evade|dodge|cheat on|not pay) (my |our |the )?(income )?tax(es)?|hide .{0,30}\bfrom (the )?(irs|tax(es)?)",
     "evading taxes"),
    (r"launder (the |my |some |dirty )?(money|cash|funds|proceeds)",
     "laundering money"),
    (r"(do|commit|profit from|get away with|use) insider trading|trade on (inside|insider|non-?public) (info|information|tips?)",
     "insider trading"),
    (r"(run|start|organi[sz]e|set up|coordinate) (a |an )?(pump[- ]and[- ]dump|ponzi( scheme)?|pyramid scheme)",
     "market manipulation or fraud schemes"),
    (r"(fake|forge|falsify|doctor) (a |my |some )?(pay ?stubs?|bank statements?|tax returns?|w-?2s?|income|documents?)",
     "falsifying financial documents"),
    (r"(steal|skim|clone|use stolen) (a |someone'?s |people'?s )?"
     r"(credit cards?|card numbers?|identit(y|ies)|bank accounts?)",
     "theft or identity fraud"),
]
_HARMFUL = [(re.compile(_INTENT + r".{0,40}?\b(" + act + r")\b", re.I), what) for act, what in _ACTS]
_INJECTION = re.compile(
    r"\b(ignore|disregard|forget|override)\b.{0,30}\b(previous|prior|above|all|your|the)\b.{0,20}"
    r"\b(instructions?|rules?|prompts?|guidelines?)\b"
    r"|\b(reveal|show|print|repeat|leak|what (is|are)|give me|tell me)\b.{0,30}"
    r"\b(system prompt|your (instructions|prompt|rules|secrets?|keys?|tokens?|config\w*)|(your |the |any )?api[ _-]?keys?"
    r"|env(ironment)? var\w*)"
    r"|\b(jailbreak|developer mode|DAN mode|act as an? unrestricted)\b", re.I)

REFUSAL_HARMFUL = ("I can't help with {what}. I'm an educational assistant, and that could break the law or hurt "
                   "people. I'm happy to explain how the rules work, how to spot scams, or how to report fraud.")
REFUSAL_INJECTION = ("I can't change my instructions or share internal details such as prompts or keys. "
                     "Ask me anything about budgeting, investing, taxes or your own numbers instead.")
REFUSAL_TOO_LONG = "That message is too long ({n:,} characters). Please keep questions under {limit:,} characters."
REFUSAL_RATE = ("You're sending questions very quickly. Please wait {wait} and try again. "
                "(Limits keep the site fast and free for everyone.)")
REFUSAL_BUSY = "The assistant has reached its usage limit for today. Please come back tomorrow."


@dataclass
class Verdict:
    allowed: bool
    message: str = ""
    reason: str = ""          # short machine-readable code for logs and tests


def check_question(text: str, max_chars: int = 1000) -> Verdict:
    """Block over-long input, prompt-injection attempts and clearly harmful requests."""
    if len(text) > max_chars:
        return Verdict(False, REFUSAL_TOO_LONG.format(n=len(text), limit=max_chars), "too_long")
    if _INJECTION.search(text):
        return Verdict(False, REFUSAL_INJECTION, "injection")
    for pattern, what in _HARMFUL:
        if pattern.search(text):
            return Verdict(False, REFUSAL_HARMFUL.format(what=what), "harmful")
    return Verdict(True)


# --- personal data: redact before anything is stored, logged or sent to an AI provider -------------------
_SSN = re.compile(r"\b(?!000|666|9\d\d)\d{3}[- ](?!00)\d{2}[- ](?!0000)\d{4}\b")
_CARD = re.compile(r"\b\d(?:[ -]?\d){12,18}\b")
_ACCOUNT = re.compile(r"\b(account|acct|routing|iban|a/c)(\s*(number|no\.?|#))?\s*[:#]?\s*"
                      r"([A-Z]{2}\d{2}[A-Z0-9]{8,30}|\d[\d -]{5,20}\d)", re.I)
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")


def _luhn_ok(digits: str) -> bool:
    total, alt = 0, False
    for d in reversed(digits):
        n = int(d)
        if alt:
            n = n * 2 - 9 if n > 4 else n * 2
        total, alt = total + n, not alt
    return total % 10 == 0


def redact_pii(text: str) -> tuple[str, list[str]]:
    """Mask SSNs, payment card numbers, labelled account/routing numbers and email addresses."""
    found: list[str] = []

    def mark(kind: str, replacement: str) -> str:
        found.append(kind)
        return replacement

    def card(m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group(0))
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            return mark("card number", "[card number removed]")
        return m.group(0)

    text = _SSN.sub(lambda m: mark("Social Security number", "[SSN removed]"), text)
    text = _CARD.sub(card, text)
    text = _ACCOUNT.sub(lambda m: mark("account number", f"{m.group(1)} [number removed]"), text)
    text = _EMAIL.sub(lambda m: mark("email address", "[email removed]"), text)
    return text, sorted(set(found))


# --- secrets: never echo keys back, even inside error messages ------------------------------------------
_SECRET = re.compile(r"(api[_-]?key|apikey|token|secret|password)=([^&\s'\"]+)"
                     r"|\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}\b|\bAIza[0-9A-Za-z_-]{30,}\b", re.I)


def redact_secrets(text: str) -> str:
    return _SECRET.sub(lambda m: f"{m.group(1)}=***" if m.group(1) else "***", text)


def safe_url(url: str | None) -> str:
    """Only allow plain web links (blocks javascript:, data: and other schemes in rendered markdown)."""
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return ""
    return url.strip() if parsed.scheme in ("http", "https") and parsed.netloc else ""


_TICKER = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")


def valid_ticker(symbol: str) -> bool:
    return bool(_TICKER.match(symbol.upper().strip()))


# --- usage limits ----------------------------------------------------------------------------------------
class _Window:
    """Counts events in a sliding time window."""

    def __init__(self, limit: int, seconds: float, clock=time.time):
        self.limit, self.seconds, self.clock, self.events = limit, seconds, clock, deque()

    def full(self) -> bool:
        now = self.clock()
        while self.events and now - self.events[0] >= self.seconds:
            self.events.popleft()
        return len(self.events) >= self.limit

    def add(self) -> None:
        self.events.append(self.clock())


class UsageGuard:
    """Per-visitor (per minute and per hour) and site-wide (per day) question limits. Thread-safe."""

    def __init__(self, per_minute: int = 8, per_hour: int = 60, site_per_day: int = 2000, clock=time.time):
        self.per_minute, self.per_hour, self.clock = per_minute, per_hour, clock
        self.site = _Window(site_per_day, 86_400, clock)
        self._visitors: dict[str, tuple[_Window, _Window]] = {}
        self._lock = threading.Lock()

    def check(self, visitor: str) -> Verdict:
        with self._lock:
            if visitor not in self._visitors:
                if len(self._visitors) > 10_000:  # bound memory on a long-running server
                    self._visitors.clear()
                self._visitors[visitor] = (_Window(self.per_minute, 60, self.clock),
                                           _Window(self.per_hour, 3600, self.clock))
            minute, hour = self._visitors[visitor]
            if minute.full():
                return Verdict(False, REFUSAL_RATE.format(wait="a minute"), "rate_minute")
            if hour.full():
                return Verdict(False, REFUSAL_RATE.format(wait="a little while"), "rate_hour")
            if self.site.full():
                return Verdict(False, REFUSAL_BUSY, "site_limit")
            for w in (minute, hour, self.site):
                w.add()
            return Verdict(True)
