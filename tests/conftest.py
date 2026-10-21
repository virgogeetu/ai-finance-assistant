import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from finance_assistant.config import Settings  # noqa: E402


def make_settings(tmp: Path) -> Settings:
    s = Settings()
    s.llm_provider = "mock"
    s.embedding_provider = "hashing"
    s.market_data_provider = "sample"
    s.alpha_vantage_key = ""
    s.cache_dir = tmp
    return s


@pytest.fixture(scope="session")
def settings(tmp_path_factory):
    return make_settings(tmp_path_factory.mktemp("cache"))


@pytest.fixture(scope="session")
def workflow(settings):
    from finance_assistant.workflow import FinanceWorkflow
    return FinanceWorkflow(settings)
