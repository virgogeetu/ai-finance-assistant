"""Provider-agnostic LLM wrapper (Gemini / OpenAI / Claude) with an offline mock.

Every agent computes a deterministic *draft* (numbers, retrieved facts) first and
then asks the LLM to turn it into a friendly explanation. If the LLM is
unavailable or fails, the draft is returned, so the system degrades gracefully.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re

from ..config import Settings

log = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.provider = settings.llm_provider
        self._model = None
        if self.provider != "mock":
            try:
                self._model = self._build()
            except Exception as exc:  # missing package or key
                log.warning("LLM provider %s unavailable (%s); using offline mock.", self.provider, exc)
                self.provider = "mock"

    @property
    def is_mock(self) -> bool:
        return self.provider == "mock"

    def _build(self):
        s = self.settings
        if s.llm_provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(model=s.model_name, temperature=s.temperature)
        if s.llm_provider == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model=s.model_name, temperature=s.temperature)
        if s.llm_provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(model=s.model_name, temperature=s.temperature, max_tokens=1200)
        raise ValueError(f"Unknown LLM_PROVIDER '{s.llm_provider}'")

    def generate(self, system: str, prompt: str, fallback: str = "") -> str:
        """Return model text, or `fallback` in mock mode / on failure."""
        if self.is_mock:
            return fallback
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            out = self._model.invoke([SystemMessage(content=system), HumanMessage(content=prompt)])
            return _text(out.content) or fallback
        except Exception as exc:
            log.error("LLM call failed: %s", exc)
            return fallback

    def describe_image(self, data: bytes, mime: str, instruction: str) -> str:
        """Send one image to a vision-capable model. Returns "" in mock mode / on failure."""
        if self.is_mock:
            return ""
        try:
            from langchain_core.messages import HumanMessage
            url = f"data:{mime};base64,{base64.b64encode(data).decode()}"
            msg = HumanMessage(content=[{"type": "text", "text": instruction},
                                        {"type": "image_url", "image_url": {"url": url}}])
            return _text(self._model.invoke([msg]).content)
        except Exception as exc:
            log.error("LLM image call failed: %s", exc)
            return ""

    def transcribe(self, audio: bytes, filename: str = "question.wav") -> str:
        """Speech-to-text for voice questions. Uses OpenAI's transcription API whenever an OpenAI key is set
        (whatever LLM_PROVIDER is); returns "" otherwise or on failure."""
        if not os.getenv("OPENAI_API_KEY"):
            return ""
        try:
            from openai import OpenAI
            out = OpenAI().audio.transcriptions.create(model=self.settings.transcribe_model, file=(filename, audio))
            return (out.text or "").strip()
        except Exception as exc:
            log.error("transcription failed: %s", exc)
            return ""

    @property
    def can_transcribe(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))

    def generate_json(self, system: str, prompt: str) -> dict | None:
        if self.is_mock:
            return None
        raw = self.generate(system + "\nRespond with JSON only, no prose, no code fences.", prompt)
        match = re.search(r"\{.*\}", raw or "", re.S)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def _text(content) -> str:
    """Normalise LangChain message content (str or list of parts)."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content).strip()
    return str(content)
