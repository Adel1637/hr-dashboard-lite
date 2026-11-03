"""Module Effectifs : combien de salariés, où, et comment l'effectif évolue."""

from __future__ import annotations

import pandas as pd

from app.charts import builders as ch
from app.core.filters import active_at, month_ends
from app.core.modules.base import Context, Module, chart, kpi, register

_PERMANENT = ("cdi", "indetermin", "permanent", "titulaire")


def _share_permanent(contracts: pd.Series) -> float | None:
    values = contracts.dropna().astype(str).str.lower()
    if values.empty:
        return None
    permanent = values.map(lambda v: any(token in v for token in _PERMANENT))
    if not permanent.any():
        return None
    return round(permanent.mean() * 100, 1)


def _top(series: pd.Series, n: int, other: str) -> pd.Series:
    counts = series.fillna("—").astype(str).value_counts()
    if len(counts) > n:
        counts = pd.concat([counts.iloc[:n], pd.Series({other: counts.iloc[n:].sum()})])
    return counts


@register
class Effectifs(Module):
    key = "effectifs"

    def compute(self, ctx: Context) -> dict:
        df, f, t = ctx.personnel, ctx.filters, ctx.t
        ref = f.period_end
        start = ref - pd.DateOffset(months=f.months)
        active = df[active_at(df, ref)]
        headcount = len(active)
        previous = int(active_at(df, start).sum())
        delta = round((headcount - previous) / previous * 100, 1) if previous else None

        points = month_ends(ref, f.months)
        trend = [int(active_at(df, p).sum()) for p in points]
        by_service = _top(active["service"], 12, t("label.other"))
        by_site = _top(active["site"], 12, t("label.other"))
        by_cat = _top(active["categorie"], 6, t("label.other"))

        return {
            "kpis": [
                kpi("headcount", headcount, "int", delta),
                kpi("permanent_share", _share_permanent(active["type_contrat"]), "pct"),
                kpi("services", int(active["service"].nunique()), "int"),
                kpi("sites", int(active["site"].nunique()), "int"),
            ],
            "charts": [
                chart("trend", ch.line(points, trend, ctx.accent, t("kpi.headcount")), wide=True),
                chart("by_service", ch.bar_h(by_service.index, by_service.values, ctx.accent)),
                chart("by_category", ch.donut(by_cat.index, by_cat.values, ctx.accent)),
                chart("by_site", ch.bar_h(by_site.index, by_site.values, ctx.accent)),
            ],
        }
