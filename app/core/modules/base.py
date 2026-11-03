"""Socle des modules RH.

Un module = une classe qui déclare les jeux de données dont il a besoin et
renvoie des indicateurs (KPI) et des graphiques. Pour ajouter un module :
créez un fichier dans ce dossier, héritez de `Module`, puis enregistrez-le
avec `@register`. Il apparaît automatiquement dans l'API et l'interface.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from app.core.filters import Filters


@dataclass
class Context:
    personnel: pd.DataFrame | None
    filters: Filters
    accent: str
    t: Callable[[str], str]


def kpi(key: str, value, fmt: str = "int", delta: float | None = None,
        hint: str | None = None) -> dict:
    """fmt : int | pct | dec | money | years — formatage fait par l'interface."""
    if value is not None and pd.isna(value):
        value = None
    elif value is not None:  # types NumPy → types Python, sérialisables en JSON
        value = int(value) if fmt in ("int", "money") else float(value)
    if delta is not None:
        delta = float(delta)
    return {"key": key, "value": value, "format": fmt, "delta": delta, "hint": hint}


def chart(key: str, figure: dict, wide: bool = False) -> dict:
    return {"key": key, "figure": figure, "wide": wide}


class Module:
    key: str = ""
    requires: tuple[str, ...] = ("personnel",)

    def compute(self, ctx: Context) -> dict:  # pragma: no cover - interface
        raise NotImplementedError


REGISTRY: dict[str, Module] = {}


def register(cls: type[Module]) -> type[Module]:
    REGISTRY[cls.key] = cls()
    return cls
