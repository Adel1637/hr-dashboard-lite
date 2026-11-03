"""État partagé de l'application (un objet par processus, attaché à `app.state`)."""

from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass, field

from app.config import Settings
from app.core.analytics import Analytics
from app.core.importer import RawTable
from app.core.store import DataStore
from app.security.ratelimit import RateLimiter
from app.security.users import UserStore

PENDING_TTL_SECONDS = 30 * 60


@dataclass
class PendingUpload:
    dataset: str
    table: RawTable
    filename: str
    signature: str
    user: str
    expires: float


@dataclass
class KitState:
    settings: Settings
    store: DataStore
    users: UserStore
    analytics: Analytics
    limiter: RateLimiter = field(default_factory=RateLimiter)
    _pending: dict[str, PendingUpload] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    @classmethod
    def create(cls, settings: Settings) -> KitState:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        store = DataStore(settings.data_dir)
        users = UserStore(settings.data_dir)
        users.bootstrap_admin(settings.admin_username, settings.admin_password)
        return cls(settings=settings, store=store, users=users,
                   analytics=Analytics(store, settings))

    # Fichiers lus mais pas encore validés (étape de correspondance).
    def add_pending(self, upload: PendingUpload) -> str:
        upload_id = secrets.token_urlsafe(16)
        now = time.monotonic()
        with self._lock:
            for key in [k for k, v in self._pending.items() if v.expires < now]:
                del self._pending[key]
            # Un seul fichier en attente par utilisateur : libère la mémoire.
            for key in [k for k, v in self._pending.items() if v.user == upload.user]:
                del self._pending[key]
            self._pending[upload_id] = upload
        return upload_id

    def pop_pending(self, upload_id: str, user: str) -> PendingUpload | None:
        with self._lock:
            upload = self._pending.get(upload_id)
            if upload is None or upload.user != user or upload.expires < time.monotonic():
                return None
            return self._pending.pop(upload_id)

    def peek_pending(self, upload_id: str, user: str) -> PendingUpload | None:
        with self._lock:
            upload = self._pending.get(upload_id)
            if upload is None or upload.user != user:
                return None
            return upload


def pending_expiry() -> float:
    return time.monotonic() + PENDING_TTL_SECONDS
