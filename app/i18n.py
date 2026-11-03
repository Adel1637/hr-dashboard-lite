"""Traductions côté serveur (libellés de séries et d'axes des graphiques)."""

from __future__ import annotations

import json
from functools import lru_cache

from app.config import LOCALES_DIR


@lru_cache(maxsize=8)
def _load(lang: str) -> dict[str, str]:
    path = LOCALES_DIR / f"{lang}.json"
    if not path.is_file():
        path = LOCALES_DIR / "fr.json"
    return json.loads(path.read_text(encoding="utf-8"))


def translator(lang: str):
    table = _load(lang)

    def t(key: str) -> str:
        return table.get(key, key)

    return t
