"""Terminal chat:  python scripts/cli.py   (type 'quit' to exit)"""
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
logging.basicConfig(level=logging.WARNING)
from finance_assistant.workflow import FinanceWorkflow  # noqa: E402

wf = FinanceWorkflow()
portfolio = json.loads((ROOT / "knowledge_base/sample_portfolios.json").read_text())["three_fund_beginner"]
print(f"AI Finance Assistant ({wf.engine}, llm={wf.llm.provider}). Sample portfolio loaded. Type 'quit' to exit.\n")
while True:
    try:
        q = input("you> ").strip()
    except (EOFError, KeyboardInterrupt):
        break
    if q.lower() in {"quit", "exit"}:
        break
    if q:
        r = wf.chat(q, "cli", portfolio=portfolio)
        print(f"\n[{', '.join(r['agents'])}]\n{r['response']}\n")
