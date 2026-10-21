"""LLM wrapper, LLM routing and embeddings with fake models (no API calls)."""
import sys
import types

import numpy as np

from finance_assistant.core.llm import LLMClient, _text
from finance_assistant.rag import embeddings
from finance_assistant.workflow.router import Router


class FakeModel:
    def __init__(self, reply="", fail=False):
        self.reply, self.fail, self.seen = reply, fail, []

    def invoke(self, messages):
        self.seen.append(messages)
        if self.fail:
            raise RuntimeError("API down")
        return types.SimpleNamespace(content=self.reply)


def client(settings, model):
    c = LLMClient(settings)
    c.provider, c._model = "openai", model
    return c


def test_mock_mode_returns_fallbacks(settings):
    c = LLMClient(settings)
    assert c.is_mock and c.generate("s", "p", fallback="draft") == "draft"
    assert c.generate_json("s", "p") is None and c.describe_image(b"x", "image/png", "read") == ""


def test_generate_and_json_parsing(settings):
    assert client(settings, FakeModel("  Hello  ")).generate("s", "p") == "Hello"
    assert client(settings, FakeModel(fail=True)).generate("s", "p", fallback="draft") == "draft"
    assert client(settings, FakeModel('Sure! {"agents": ["tax_education"]} done')).generate_json("s", "p") == {
        "agents": ["tax_education"]}
    assert client(settings, FakeModel("no json here")).generate_json("s", "p") is None
    assert client(settings, FakeModel("{bad json}")).generate_json("s", "p") is None


def test_describe_image_sends_a_data_url(settings):
    model = FakeModel("Balance $10")
    assert client(settings, model).describe_image(b"\x89PNG", "image/png", "read it") == "Balance $10"
    part = model.seen[0][0].content[1]
    assert part["type"] == "image_url" and part["image_url"]["url"].startswith("data:image/png;base64,")
    assert client(settings, FakeModel(fail=True)).describe_image(b"x", "image/png", "read") == ""


def test_text_normalises_message_parts():
    assert _text([{"text": "a"}, "b", {"type": "x"}]) == "ab"
    assert _text(42) == "42"


def test_unknown_or_unavailable_provider_falls_back_to_mock(settings):
    s = type(settings)(**{**settings.__dict__, "llm_provider": "nonsense"})
    assert LLMClient(s).is_mock


def test_build_picks_the_langchain_class(settings, monkeypatch):
    made = {}
    for mod, cls in [("langchain_openai", "ChatOpenAI"), ("langchain_anthropic", "ChatAnthropic"),
                     ("langchain_google_genai", "ChatGoogleGenerativeAI")]:
        monkeypatch.setitem(sys.modules, mod, types.SimpleNamespace(**{cls: lambda cls=cls, **kw: made.setdefault(cls, kw)}))
    for provider in ("openai", "anthropic", "gemini"):
        s = type(settings)(**{**settings.__dict__, "llm_provider": provider, "llm_model": ""})
        assert not LLMClient(s).is_mock
    assert made["ChatOpenAI"]["model"] == "gpt-4o-mini" and made["ChatAnthropic"]["max_tokens"] == 1200


def test_transcribe_uses_openai_when_key_present(settings, monkeypatch):
    c = LLMClient(settings)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert not c.can_transcribe and c.transcribe(b"wav") == ""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    sent = {}

    class FakeOpenAI:
        def __init__(self):
            self.audio = types.SimpleNamespace(transcriptions=types.SimpleNamespace(create=self.create))

        def create(self, model, file):
            sent.update(model=model, name=file[0])
            return types.SimpleNamespace(text=" What is an ETF? ")
    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))
    assert c.can_transcribe and c.transcribe(b"wav", "q.wav") == "What is an ETF?"
    assert sent == {"model": settings.transcribe_model, "name": "q.wav"}

    class Broken:
        def __init__(self):
            raise RuntimeError("no network")
    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=Broken))
    assert c.transcribe(b"wav") == ""


def test_llm_router_uses_model_choice_and_falls_back(settings):
    good = client(settings, FakeModel('{"agents": ["tax_education", "made_up"], "reason": "about IRAs"}'))
    assert Router(good).route("Tell me about IRAs") == (["tax_education"], "llm: about IRAs")
    bad = client(settings, FakeModel('{"agents": ["made_up"]}'))
    route, reason = Router(bad).route("What is an expense ratio?")
    assert route == ["finance_qa"] and not reason.startswith("llm")


def test_embedder_selection_and_langchain_adapter(settings, monkeypatch):
    assert isinstance(embeddings.get_embedder(settings), embeddings.HashingEmbedder)

    class FakeLC:
        def __init__(self, model):
            self.model = model

        def embed_documents(self, texts):
            return [[3.0, 4.0], [0.0, 0.0]][: len(texts)]

        def embed_query(self, text):
            return [0.0, 2.0]
    monkeypatch.setitem(sys.modules, "langchain_openai", types.SimpleNamespace(OpenAIEmbeddings=FakeLC))
    s = type(settings)(**{**settings.__dict__, "embedding_provider": "openai"})
    e = embeddings.get_embedder(s)
    docs = e.embed_documents(["a", "b"])
    assert np.allclose(docs[0], [0.6, 0.8]) and np.allclose(docs[1], [0, 0])  # zero vectors stay zero
    assert np.allclose(e.embed_query("q"), [0, 1])
    monkeypatch.setitem(sys.modules, "langchain_google_genai", types.SimpleNamespace())  # missing class
    s.embedding_provider = "gemini"
    assert isinstance(embeddings.get_embedder(s), embeddings.HashingEmbedder)
    assert embeddings.HashingEmbedder().embed_documents([]).shape == (0, 1024)
