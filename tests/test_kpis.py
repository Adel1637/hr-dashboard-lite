"""Indicateurs calculés sur un petit jeu construit à la main : résultats vérifiables."""

from datetime import date

import pandas as pd
import pytest

from app.core.filters import Filters, active_at, apply_filters, average_headcount, month_ends
from app.core.modules import REGISTRY, Context
from app.i18n import translator


def staff() -> pd.DataFrame:
    rows = [
        # matricule, entrée, sortie, sexe, naissance, service, site, catégorie, contrat, motif
        ("A", "2015-01-01", None, "F", "1970-06-01", "Prod", "Nord", "Cadre", "CDI", None),
        ("B", "2018-05-01", None, "H", "1990-06-01", "Prod", "Nord", "Exécution", "CDI", None),
        ("C", "2020-01-01", "2026-03-15", "H", "1985-06-01", "Prod", "Sud", "Exécution", "CDD",
         "Fin de contrat"),
        ("D", "2026-02-01", None, "F", "2000-06-01", "RH", "Sud", "Maîtrise", "CDD", None),
        ("E", "2010-01-01", "2026-06-30", "H", "1964-06-01", "RH", "Nord", "Cadre", "CDI",
         "Retraite"),
    ]
    frame = pd.DataFrame(rows, columns=["matricule", "date_entree", "date_sortie", "sexe",
                                        "date_naissance", "service", "site", "categorie",
                                        "type_contrat", "motif_sortie"])
    for col in ("date_entree", "date_sortie", "date_naissance"):
        frame[col] = pd.to_datetime(frame[col])
    frame["nom"] = frame["matricule"]
    return frame


def run(module: str, ref=date(2026, 10, 31), months=12, values=None):
    filters = Filters.build(ref, months, values or {})
    people = apply_filters(staff(), filters)
    ctx = Context(personnel=people, filters=filters,
                  accent="#0D9488", t=translator("fr"))
    result = REGISTRY[module].compute(ctx)
    return {k["key"]: k["value"] for k in result["kpis"]}, result


def test_active_at_excludes_people_who_left():
    frame = staff()
    assert active_at(frame, pd.Timestamp("2026-01-15")).sum() == 4   # A, B, C, E
    assert active_at(frame, pd.Timestamp("2026-10-31")).sum() == 3   # A, B, D


def test_headcount_and_delta():
    kpis, result = run("effectifs")
    assert kpis["headcount"] == 3
    # 31/10/2025 : A, B, C, E présents → 4 ; variation (3 - 4) / 4 = -25 %
    assert result["kpis"][0]["delta"] == -25.0
    assert kpis["permanent_share"] == pytest.approx(66.7, abs=0.1)
    assert kpis["sites"] == 2


def test_filters_restrict_population():
    kpis, _ = run("effectifs", values={"site": ["Sud"]})
    assert kpis["headcount"] == 1


def test_average_headcount_and_month_ends():
    frame = staff()
    points = month_ends(pd.Timestamp("2026-10-31"), 12)
    assert len(points) == 12 and points[-1] == pd.Timestamp("2026-10-31")
    avg = average_headcount(frame, pd.Timestamp("2025-11-01"), pd.Timestamp("2026-10-31"))
    assert 3 <= avg <= 4


def test_every_chart_is_json_ready():
    import json
    _, result = run("effectifs")
    json.dumps(result)
