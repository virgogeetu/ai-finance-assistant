"""Central configuration, read from environment variables (.env supported)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:  # optional
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

ROOT = Path(__file__).resolve().parents[2]

DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-5-5",
}


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


@dataclass
class Settings:
    # LLM
    llm_provider: str = field(default_factory=lambda: _env("LLM_PROVIDER", "mock").lower())
    llm_model: str = field(default_factory=lambda: _env("LLM_MODEL"))
    temperature: float = field(default_factory=lambda: float(_env("LLM_TEMPERATURE", "0.2")))
    transcribe_model: str = field(default_factory=lambda: _env("TRANSCRIBE_MODEL", "whisper-1"))  # voice input

    # Embeddings / RAG
    embedding_provider: str = field(default_factory=lambda: _env("EMBEDDING_PROVIDER", "hashing").lower())
    embedding_model: str = field(default_factory=lambda: _env("EMBEDDING_MODEL"))
    chunk_size: int = 600          # characters
    chunk_overlap: int = 100
    top_k: int = 4
    min_relevance: float = 0.12    # hybrid score threshold

    # Market data
    market_data_provider: str = field(default_factory=lambda: _env("MARKET_DATA_PROVIDER", "auto").lower())
    alpha_vantage_key: str = field(default_factory=lambda: _env("ALPHA_VANTAGE_API_KEY"))
    av_calls_per_minute: int = 5   # Alpha Vantage free tier
    av_calls_per_day: int = 25
    quote_ttl: int = 60 * 5        # seconds
    daily_ttl: int = 60 * 60 * 6
    news_ttl: int = 60 * 30

    # Workflow
    max_agents_per_turn: int = 3
    history_window: int = 8        # messages passed to agents

    # Guardrails (public deployment); override with env vars or hosting secrets
    max_question_chars: int = field(default_factory=lambda: int(_env("MAX_QUESTION_CHARS", "1000")))
    questions_per_minute: int = field(default_factory=lambda: int(_env("QUESTIONS_PER_MINUTE", "8")))
    questions_per_hour: int = field(default_factory=lambda: int(_env("QUESTIONS_PER_HOUR", "60")))
    site_questions_per_day: int = field(default_factory=lambda: int(_env("SITE_QUESTIONS_PER_DAY", "2000")))
    max_files_per_message: int = field(default_factory=lambda: int(_env("MAX_FILES_PER_MESSAGE", "5")))
    max_upload_mb: int = field(default_factory=lambda: int(_env("MAX_UPLOAD_MB", "10")))

    # Paths
    kb_dir: Path = ROOT / "knowledge_base"
    cache_dir: Path = ROOT / ".cache"

    @property
    def model_name(self) -> str:
        return self.llm_model or DEFAULT_MODELS.get(self.llm_provider, "")

    @property
    def index_dir(self) -> Path:
        return self.cache_dir / f"index_{self.embedding_provider}"


def get_settings() -> Settings:
    return Settings()
