"""Cache en mémoire avec durée de vie, vidé à chaque nouvel import.

Remplace un cache permanent : les indicateurs restent rapides, mais ne
deviennent jamais périmés après l'import d'un nouveau fichier.
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Hashable
from typing import Any


class TTLCache:
    def __init__(self, ttl_seconds: int = 600, maxsize: int = 256) -> None:
        self.ttl = ttl_seconds
        self.maxsize = maxsize
        self._items: OrderedDict[Hashable, tuple[float, Any]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: Hashable) -> Any | None:
        with self._lock:
            item = self._items.get(key)
            if item is None:
                return None
            expires, value = item
            if expires < time.monotonic():
                del self._items[key]
                return None
            self._items.move_to_end(key)
            return value

    def set(self, key: Hashable, value: Any) -> None:
        with self._lock:
            self._items[key] = (time.monotonic() + self.ttl, value)
            self._items.move_to_end(key)
            while len(self._items) > self.maxsize:
                self._items.popitem(last=False)

    def get_or_compute(self, key: Hashable, compute: Callable[[], Any]) -> Any:
        value = self.get(key)
        if value is None:
            value = compute()
            self.set(key, value)
        return value

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def __len__(self) -> int:
        return len(self._items)
