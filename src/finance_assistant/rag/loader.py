"""Load knowledge-base articles and glossary as documents."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Document:
    id: str
    title: str
    category: str
    text: str
    url: str = ""
    tags: list[str] = field(default_factory=list)
    kind: str = "kb"  # kb | glossary


def load_articles(kb_dir: Path) -> list[Document]:
    data = json.loads((kb_dir / "articles.json").read_text())
    return [Document(id=a["id"], title=a["title"], category=a["category"], text=a["content"],
                     url=a.get("further_reading", ""), tags=a.get("tags", [])) for a in data]


def load_glossary(kb_dir: Path) -> dict[str, str]:
    data = json.loads((kb_dir / "glossary.json").read_text())
    return {g["term"]: g["definition"] for g in data}


def glossary_documents(glossary: dict[str, str]) -> list[Document]:
    return [Document(id=f"glossary-{i}", title=term, category="glossary", text=f"{term}: {d}", kind="glossary")
            for i, (term, d) in enumerate(glossary.items())]


def load_all(kb_dir: Path) -> list[Document]:
    return load_articles(kb_dir) + glossary_documents(load_glossary(kb_dir))
