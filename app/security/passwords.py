"""Hachage des mots de passe avec scrypt (bibliothèque standard, sans dépendance)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

_N, _R, _P, _DKLEN = 2**14, 8, 1, 32
MIN_LENGTH = 10


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=_DKLEN)
    salt_b64 = base64.b64encode(salt).decode()
    digest_b64 = base64.b64encode(digest).decode()
    return f"scrypt${_N}${_R}${_P}${salt_b64}${digest_b64}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt_b64, digest_b64 = stored.split("$")
        if algo != "scrypt":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        digest = hashlib.scrypt(password.encode(), salt=salt, n=int(n), r=int(r), p=int(p),
                                dklen=len(expected))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, expected)


def check_strength(password: str) -> str | None:
    """Renvoie un message d'erreur, ou None si le mot de passe est acceptable."""
    if len(password) < MIN_LENGTH:
        return f"Le mot de passe doit contenir au moins {MIN_LENGTH} caractères."
    if password.isdigit() or password.isalpha():
        return "Le mot de passe doit mélanger lettres et chiffres ou symboles."
    return None


# Hachage factice : vérifié quand l'utilisateur n'existe pas, pour que le temps
# de réponse ne révèle pas quels identifiants existent.
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))
