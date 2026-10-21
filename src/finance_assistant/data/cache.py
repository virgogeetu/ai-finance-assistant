"""TTL cache with optional disk persistence and stale reads."""
from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Any


class TTLCache:
    def __init__(self, directory: Path | None = None):
        self._mem: dict[str, tuple[float, float, Any]] = {}  # key -> (stored_at, ttl, value)
        self._dir = directory
        self._lock = threading.Lock()
        if directory:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except OSError:
                self._dir = None

    def _file(self, key: str) -> Path | None:
        return self._dir / (hashlib.sha1(key.encode()).hexdigest() + ".json") if self._dir else None

    def set(self, key: str, value: Any, ttl: float) -> None:
        entry = (time.time(), ttl, value)
        with self._lock:
            self._mem[key] = entry
        f = self._file(key)
        if f:
            try:
                f.write_text(json.dumps({"stored_at": entry[0], "ttl": ttl, "value": value}))
            except (OSError, TypeError):
                pass

    def get(self, key: str, allow_stale: bool = False) -> tuple[Any, float, bool] | None:
        """Return (value, stored_at, is_fresh) or None."""
        with self._lock:
            entry = self._mem.get(key)
        if entry is None:
            f = self._file(key)
            if f and f.exists():
                try:
                    raw = json.loads(f.read_text())
                    entry = (raw["stored_at"], raw["ttl"], raw["value"])
                    with self._lock:
                        self._mem[key] = entry
                except (OSError, ValueError, KeyError):
                    entry = None
        if entry is None:
            return None
        stored_at, ttl, value = entry
        fresh = time.time() - stored_at < ttl
        if fresh or allow_stale:
            return value, stored_at, fresh
        return None
