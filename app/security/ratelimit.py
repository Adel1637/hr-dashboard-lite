"""Limitation du nombre de requêtes par clé (IP + action), fenêtre glissante.

En mémoire : adapté à un serveur unique. Pour plusieurs processus, remplacez
cette classe par une implémentation Redis avec la même interface `hit`.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, window_seconds: int = 60) -> None:
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int) -> bool:
        """Enregistre une tentative ; renvoie False si la limite est dépassée."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= now - self.window:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
