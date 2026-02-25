import hashlib
import json
import time
from typing import Any, Callable, Dict, Optional, Tuple


class APICache:
    def __init__(self, ttl: int = 300):
        self._store: Dict[str, Tuple[Any, float]] = {}
        self._ttl = ttl

    def make_key(self, method: str, **kwargs) -> str:
        raw = json.dumps({"method": method, **kwargs}, default=str, sort_keys=True)
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        if key in self._store:
            data, ts = self._store[key]
            if time.time() - ts < self._ttl:
                return data
            del self._store[key]
        return None

    def set(self, key: str, data: Any) -> None:
        self._store[key] = (data, time.time())

    def clear(self) -> None:
        self._store.clear()

    def get_or_fetch(self, key: str, fetch_fn: Callable) -> Any:
        cached = self.get(key)
        if cached is not None:
            return cached
        data = fetch_fn()
        self.set(key, data)
        return data
