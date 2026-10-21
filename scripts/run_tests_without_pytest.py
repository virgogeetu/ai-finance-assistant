"""Minimal runner for environments without pytest (CI uses pytest)."""
import inspect
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
import types
sys.modules.setdefault("pytest", types.SimpleNamespace(fixture=lambda *a, **k: (lambda f: f)))
import conftest  # noqa: E402

tmp = Path(tempfile.mkdtemp())
settings = conftest.make_settings(tmp / "cache")
from finance_assistant.workflow import FinanceWorkflow  # noqa: E402
fixtures = {"settings": settings, "workflow": FinanceWorkflow(settings)}
passed = failed = 0
for mod in ["test_utils", "test_rag", "test_market_data", "test_workflow"]:
    m = __import__(mod)
    for name, fn in inspect.getmembers(m, inspect.isfunction):
        if not name.startswith("test_"):
            continue
        args = {}
        for p in inspect.signature(fn).parameters:
            args[p] = fixtures.get(p) or Path(tempfile.mkdtemp())
        try:
            fn(**args)
            passed += 1
            print(f"PASS {mod}.{name}")
        except Exception:
            failed += 1
            print(f"FAIL {mod}.{name}")
            traceback.print_exc()
print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
