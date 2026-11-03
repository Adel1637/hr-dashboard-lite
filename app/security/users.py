"""Compte administrateur unique de l'édition Lite, stocké dans DATA_DIR/users.json.

La gestion de plusieurs comptes et rôles fait partie de la version Pro.
"""

from __future__ import annotations

import json
import logging
import re
import secrets
import threading
from dataclasses import asdict, dataclass
from pathlib import Path

from app.security.passwords import (
    DUMMY_HASH,
    check_strength,
    hash_password,
    verify_password,
)

log = logging.getLogger("kit.users")
_USERNAME = re.compile(r"^[a-zA-Z0-9._-]{3,40}$")


class UserError(ValueError):
    pass


@dataclass
class User:
    username: str
    role: str
    password_hash: str
    token_version: int = 0  # incrémenté pour révoquer les jetons existants

    def public(self) -> dict:
        return {"username": self.username, "role": self.role}


class UserStore:
    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / "users.json"
        self._lock = threading.Lock()
        self._users: dict[str, User] = {}
        if self.path.is_file():
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self._users = {u["username"]: User(**u) for u in raw}

    def _save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps([asdict(u) for u in self._users.values()], indent=2),
                       encoding="utf-8")
        tmp.replace(self.path)

    def bootstrap_admin(self, username: str, password: str) -> None:
        """Crée le premier administrateur si aucun compte n'existe."""
        if self._users:
            return
        generated = not password
        if generated:
            password = secrets.token_urlsafe(14)
        self.create(username, password, "admin", enforce_strength=not generated)
        if generated:
            log.warning("Compte administrateur créé : %s / %s — changez ce mot de passe.",
                        username, password)

    def create(self, username: str, password: str, role: str,
               enforce_strength: bool = True) -> User:
        if not _USERNAME.match(username):
            raise UserError("Identifiant : 3 à 40 caractères (lettres, chiffres, . _ -).")
        if role != "admin":
            raise UserError("L'édition Lite ne gère qu'un compte administrateur.")
        if enforce_strength and (problem := check_strength(password)):
            raise UserError(problem)
        with self._lock:
            if username in self._users:
                raise UserError("Cet identifiant existe déjà.")
            user = User(username=username, role=role, password_hash=hash_password(password))
            self._users[username] = user
            self._save()
        return user


    def change_password(self, username: str, password: str) -> None:
        if problem := check_strength(password):
            raise UserError(problem)
        with self._lock:
            user = self._users[username]
            user.password_hash = hash_password(password)
            user.token_version += 1  # déconnecte les autres sessions
            self._save()

    def authenticate(self, username: str, password: str) -> User | None:
        user = self._users.get(username)
        if user is None:
            verify_password(password, DUMMY_HASH)
            return None
        return user if verify_password(password, user.password_hash) else None

    def get(self, username: str) -> User | None:
        return self._users.get(username)


