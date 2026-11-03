"""Filtres globaux et outils de dates communs à tous les modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

FILTER_COLUMNS = ("site", "service", "categorie", "type_contrat", "sexe")


@dataclass(frozen=True)
class Filters:
    """Filtres de l'utilisateur. Une liste vide signifie « tout »."""

    ref_date: date
    months: int = 12
    values: tuple[tuple[str, tuple[str, ...]], ...] = field(default=())

    @property
    def period_start(self) -> pd.Timestamp:
        ref = pd.Timestamp(self.ref_date)
        return (ref - pd.DateOffset(months=self.months)).normalize() + pd.Timedelta(days=1)

    @property
    def period_end(self) -> pd.Timestamp:
        return pd.Timestamp(self.ref_date)

    def as_dict(self) -> dict[str, tuple[str, ...]]:
        return dict(self.values)

    @classmethod
    def build(cls, ref_date: date, months: int, raw: dict[str, list[str]]) -> Filters:
        values = tuple(
            (col, tuple(sorted(set(raw[col]))))
            for col in FILTER_COLUMNS if raw.get(col)
        )
        return cls(ref_date=ref_date, months=max(1, min(months, 60)), values=values)


def apply_filters(frame: pd.DataFrame, filters: Filters) -> pd.DataFrame:
    mask = pd.Series(True, index=frame.index)
    for column, allowed in filters.values:
        if column in frame.columns and allowed:
            mask &= frame[column].astype(str).isin(allowed)
    return frame[mask]


def active_at(frame: pd.DataFrame, when: pd.Timestamp) -> pd.Series:
    """Salariés présents à une date : entrés avant, pas encore sortis."""
    return (frame["date_entree"] <= when) & (
        frame["date_sortie"].isna() | (frame["date_sortie"] > when)
    )


def month_ends(end: pd.Timestamp, months: int) -> list[pd.Timestamp]:
    last = end.normalize()
    points = [last]
    for i in range(1, months):
        points.append((last - pd.DateOffset(months=i)) + pd.offsets.MonthEnd(0))
    return sorted(points)


def average_headcount(frame: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> float:
    """Effectif moyen : moyenne des effectifs aux fins de mois de la période."""
    months = max(1, (end.year - start.year) * 12 + end.month - start.month + 1)
    points = month_ends(end, months)
    counts = [int(active_at(frame, p).sum()) for p in points]
    return sum(counts) / len(counts) if counts else 0.0


def filter_options(frame: pd.DataFrame | None) -> dict[str, list[str]]:
    if frame is None:
        return {col: [] for col in FILTER_COLUMNS}
    return {
        col: sorted(frame[col].dropna().astype(str).unique().tolist())
        if col in frame.columns else []
        for col in FILTER_COLUMNS
    }
