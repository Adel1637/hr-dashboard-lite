"""Générateur de données RH fictives et réalistes.

Toutes les données sont inventées (noms, sites, services). Les noms de
colonnes sont volontairement différents du schéma canonique, pour montrer
l'assistant de correspondance en action.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

SERVICES = {
    "Production": 0.30, "Maintenance": 0.14, "Logistique": 0.11, "Qualité": 0.07,
    "Commercial": 0.09, "Finance": 0.06, "Ressources humaines": 0.05,
    "Informatique": 0.06, "Achats": 0.04, "HSE": 0.04, "Direction générale": 0.04,
}
SITES = {"Siège": 0.22, "Site Nord": 0.26, "Site Sud": 0.20, "Site Est": 0.18, "Site Ouest": 0.14}
CATEGORIES = {"Cadre": 0.18, "Maîtrise": 0.32, "Exécution": 0.50}
CONTRACTS = {"CDI": 0.80, "CDD": 0.17, "Apprentissage": 0.03}
EXIT_REASONS = {"Démission": 0.42, "Fin de contrat": 0.25, "Licenciement": 0.08,
                "Mutation": 0.10, "Autre": 0.05}
FIRST_F = ["Amina", "Sarah", "Lina", "Nadia", "Yasmine", "Claire", "Inès", "Meriem", "Laura",
           "Salma", "Emma", "Rania", "Léa", "Hana", "Julie", "Nour", "Camille", "Imane"]
FIRST_H = ["Karim", "Yanis", "Thomas", "Mehdi", "Lucas", "Amine", "Hugo", "Sofiane", "Adam",
           "Rayan", "Nicolas", "Bilal", "Louis", "Walid", "Samir", "Mathis", "Omar", "Anis"]
LAST = ["Benali", "Martin", "Haddad", "Bernard", "Mansouri", "Petit", "Saidi", "Robert",
        "Belkacem", "Richard", "Cherif", "Durand", "Rahmani", "Moreau", "Larbi", "Laurent",
        "Ziani", "Simon", "Hamdi", "Michel", "Bouzid", "Garcia", "Amrani", "David"]


def _pick(rng: np.random.Generator, options: dict[str, float], size: int) -> np.ndarray:
    keys = list(options)
    probs = np.array(list(options.values()), dtype=float)
    return rng.choice(keys, size=size, p=probs / probs.sum())


def generate_personnel(size: int = 1000, end: date | None = None, seed: int = 7) -> pd.DataFrame:
    """Registre du personnel : `size` salariés présents environ à la date de fin."""
    rng = np.random.default_rng(seed)
    end_ts = pd.Timestamp(end or date.today()).normalize()
    history_start = end_ts - pd.DateOffset(years=4)
    annual_exit_rate = 0.11

    # Effectif initial (présent au début de l'historique) + flux sur 4 ans.
    initial = int(size * 0.95)
    hires = int(size * annual_exit_rate * 4 * 1.15)
    total = initial + hires

    entry = np.empty(total, dtype="datetime64[ns]")
    span_old = (history_start - pd.Timestamp("1990-01-01")).days
    entry[:initial] = (pd.Timestamp("1990-01-01")
                       + pd.to_timedelta(rng.beta(2.2, 1.4, initial) * span_old, unit="D"))
    span_new = (end_ts - history_start).days
    entry[initial:] = history_start + pd.to_timedelta(rng.uniform(0, span_new, hires), unit="D")
    entry = pd.to_datetime(entry).normalize()

    seniority_at_start = np.maximum((history_start - entry).days / 365.25, 0)
    age_at_entry = np.clip(rng.normal(29, 6.5, total), 19, 55)
    birth = entry - pd.to_timedelta(age_at_entry * 365.25, unit="D")

    contract = _pick(rng, CONTRACTS, total)
    contract[seniority_at_start > 3] = "CDI"
    sex = rng.choice(["F", "H"], size=total, p=[0.34, 0.66])

    window_start = pd.DatetimeIndex(np.maximum(entry.values, history_start.to_datetime64()))
    window_days = np.asarray((end_ts - window_start).days, dtype=float)

    # Retraites : entre 60 et 62 ans, si cette date tombe dans l'historique.
    retire = birth + pd.to_timedelta(rng.integers(60, 63, total) * 365.25, unit="D")
    retiring = np.asarray((retire > window_start) & (retire <= end_ts))

    # Autres départs : probabilité plus forte pour les contrats non permanents.
    yearly = np.where(contract != "CDI", annual_exit_rate * 2.2, annual_exit_rate * 0.85)
    leave_prob = 1 - (1 - yearly) ** (window_days / 365.25)
    leaving = (rng.random(total) < leave_prob) & ~retiring
    offset = rng.uniform(30, np.maximum(31, window_days))
    leave_date = window_start + pd.to_timedelta(offset, unit="D")

    exit_dates = pd.Series(pd.NaT, index=range(total), dtype="datetime64[ns]")
    exit_dates[retiring] = retire[retiring].normalize()
    exit_dates[leaving] = leave_date[leaving].normalize()
    exit_dates[exit_dates > end_ts] = pd.NaT

    reasons = pd.Series(_pick(rng, EXIT_REASONS, total), dtype="object")
    contract_end = (contract != "CDI") & (rng.random(total) < 0.7)
    reasons[contract_end] = "Fin de contrat"
    reasons[retiring] = "Retraite"
    reasons[exit_dates.isna().to_numpy()] = pd.NA

    service = _pick(rng, SERVICES, total)
    category = _pick(rng, CATEGORIES, total)
    category[(service == "Direction générale") & (rng.random(total) < 0.6)] = "Cadre"
    first = np.where(sex == "F", rng.choice(FIRST_F, total), rng.choice(FIRST_H, total))
    names = [f"{ln.upper()} {fn}" for ln, fn in zip(rng.choice(LAST, total), first, strict=True)]

    frame = pd.DataFrame({
        "Matricule": [f"E{10000 + i}" for i in range(total)],
        "Nom et prénom": names,
        "Genre": np.where(sex == "F", "Femme", "Homme"),
        "Date de naissance": birth.date,
        "Date d'embauche": entry.date,
        "Date de départ": exit_dates.dt.date,
        "Motif de départ": reasons,
        "Direction": service,
        "Site": _pick(rng, SITES, total),
        "CSP": category,
        "Contrat": contract,
    })
    # Les salariés sortis avant l'historique ne figurent pas dans le registre.
    return frame.sort_values("Matricule").reset_index(drop=True)


def write_xlsx(frame: pd.DataFrame, path, title: str) -> None:
    """Écrit un classeur avec une ligne de titre au-dessus de l'en-tête, comme
    beaucoup d'exports réels ; l'import la détecte et l'ignore."""
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, startrow=2, sheet_name="Données")
        writer.sheets["Données"]["A1"] = title
