"""Correspondance entre les colonnes d'un fichier client et le schéma canonique.

`suggest_mapping` propose une correspondance automatique ; `apply_mapping`
convertit les types, contrôle chaque ligne et produit un rapport d'erreurs
lisible (numéro de ligne tel qu'affiché dans Excel).
"""

from __future__ import annotations

import difflib
import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime

import pandas as pd

from app.schemas import DatasetSchema

MAX_REPORTED_ERRORS = 200
_EMPTY = {"", "nan", "nat", "none", "null", "-", "n/a", "na"}
_FEMALE = {"f", "femme", "feminin", "female", "w", "woman", "fille"}
_MALE = {"h", "m", "homme", "masculin", "male", "man"}


class MappingError(ValueError):
    pass


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def columns_signature(columns: list[str]) -> str:
    """Empreinte stable d'une structure de fichier, pour réutiliser un mapping."""
    joined = "|".join(sorted(normalize(c) for c in columns))
    return hashlib.sha256(joined.encode()).hexdigest()[:16]


def _score(column: str, synonyms: tuple[str, ...]) -> float:
    col = normalize(column)
    if not col:
        return 0.0
    best = 0.0
    for syn in synonyms:
        if col == syn:
            return 1.0
        if len(syn) >= 4 and (f" {syn} " in f" {col} " or f" {col} " in f" {syn} "):
            best = max(best, 0.85)
        best = max(best, difflib.SequenceMatcher(None, col, syn).ratio() * 0.9)
    return best


def suggest_mapping(columns: list[str], schema: DatasetSchema,
                    threshold: float = 0.75) -> dict[str, str | None]:
    candidates = []
    for f in schema.fields:
        for col in columns:
            score = _score(col, f.synonyms + (f.key.replace("_", " "),))
            if score >= threshold:
                candidates.append((score, f.key, col))
    candidates.sort(key=lambda c: -c[0])
    mapping: dict[str, str | None] = {f.key: None for f in schema.fields}
    used: set[str] = set()
    for _, key, col in candidates:
        if mapping[key] is None and col not in used:
            mapping[key] = col
            used.add(col)
    return mapping


# Codes d'erreur de ligne ; le libellé affiché vient des fichiers de langue (import.err.<code>).
ERROR_CODES = ("invalid_rejected", "invalid_ignored", "required_empty", "exit_before_hire")


@dataclass
class ImportReport:
    rows_total: int = 0
    rows_accepted: int = 0
    rows_rejected: int = 0
    errors: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, row: int, field_key: str, value, message: str, code: str = "") -> None:
        if len(self.errors) < MAX_REPORTED_ERRORS:
            self.errors.append({"row": int(row), "field": field_key,
                                "value": "" if value is None else str(value)[:80],
                                "message": message, "code": code})

    def as_dict(self) -> dict:
        return {
            "rows_total": self.rows_total,
            "rows_accepted": self.rows_accepted,
            "rows_rejected": self.rows_rejected,
            "errors": self.errors,
            "errors_truncated": self.rows_rejected > len(self.errors),
            "warnings": self.warnings,
        }


def _is_empty(series: pd.Series) -> pd.Series:
    return series.isna() | series.astype(str).str.strip().str.lower().isin(_EMPTY)


def _to_text(series: pd.Series) -> pd.Series:
    out = series.astype(str).str.strip()
    # Les matricules numériques lus par Excel arrivent en "1024.0".
    out = out.str.replace(r"^(\d+)\.0$", r"\1", regex=True)
    return out.mask(_is_empty(series))


def _to_date(series: pd.Series) -> pd.Series:
    empty = _is_empty(series)
    result = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    numeric = pd.to_numeric(series, errors="coerce")
    serial = numeric.between(1, 80_000) & ~empty
    if serial.any():  # dates Excel restées en nombre de jours
        result[serial] = pd.to_datetime(numeric[serial], unit="D", origin="1899-12-30")
    rest = ~serial & ~empty
    if rest.any():
        values = series[rest]
        parsed = pd.Series(pd.NaT, index=values.index, dtype="datetime64[ns]")
        is_ts = values.map(lambda v: isinstance(v, datetime | date))
        if is_ts.any():
            parsed[is_ts] = pd.to_datetime(values[is_ts], errors="coerce")
        text = values[~is_ts].astype(str).str.strip()
        if not text.empty:
            iso = text.str.match(r"^\d{4}-\d{2}-\d{2}")
            parsed[text.index[iso]] = pd.to_datetime(text[iso].str[:10], format="%Y-%m-%d",
                                                     errors="coerce")
            parsed[text.index[~iso]] = pd.to_datetime(text[~iso], dayfirst=True,
                                                      format="mixed", errors="coerce")
        result[rest] = parsed
    return result.dt.normalize()


def _to_number(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.replace(r"[\s ]", "", regex=True).str.replace(",", ".")
    out = pd.to_numeric(text, errors="coerce")
    return out.mask(_is_empty(series))


def _to_sex(series: pd.Series) -> pd.Series:
    norm = series.astype(str).map(normalize)
    out = pd.Series(pd.NA, index=series.index, dtype="object")
    out[norm.isin(_FEMALE)] = "F"
    out[norm.isin(_MALE)] = "H"
    return out


_CONVERTERS = {"str": _to_text, "date": _to_date, "number": _to_number, "sex": _to_sex}


def apply_mapping(frame: pd.DataFrame, schema: DatasetSchema, mapping: dict[str, str | None],
                  header_row: int = 0,
                  excel_rows: list[int] | None = None) -> tuple[pd.DataFrame, ImportReport]:
    missing = [k for k in schema.required_keys if not mapping.get(k)]
    if missing:
        raise MappingError("Champs obligatoires non reliés : " + ", ".join(missing))
    unknown = [c for c in mapping.values() if c and c not in frame.columns]
    if unknown:
        raise MappingError("Colonnes introuvables dans le fichier : " + ", ".join(unknown))

    report = ImportReport(rows_total=len(frame))
    # Numéro de ligne tel qu'affiché dans Excel. Si `excel_rows` est fourni (import réel), il tient
    # compte des lignes vides ; sinon on suppose un tableau compact sous l'en-tête.
    excel_row = pd.Index(excel_rows) if excel_rows is not None else frame.index + header_row + 2
    out = pd.DataFrame(index=frame.index)
    rejected = pd.Series(False, index=frame.index)

    for f in schema.fields:
        column = mapping.get(f.key)
        if not column:
            out[f.key] = pd.NaT if f.type == "date" else pd.NA
            continue
        source = frame[column]
        converted = _CONVERTERS[f.type](source)
        invalid = converted.isna() & ~_is_empty(source)
        missing_required = converted.isna() & _is_empty(source) if f.required else None

        for idx in source.index[invalid]:
            msg = "valeur invalide" + (" (ligne rejetée)" if f.required else " (ignorée)")
            report.add_error(excel_row[frame.index.get_loc(idx)], f.key, source[idx], msg,
                             "invalid_rejected" if f.required else "invalid_ignored")
        if f.required:
            rejected |= invalid
            for idx in source.index[missing_required]:
                report.add_error(excel_row[frame.index.get_loc(idx)], f.key, "",
                                 "champ obligatoire vide (ligne rejetée)", "required_empty")
            rejected |= missing_required
        out[f.key] = converted

    if schema.key == "personnel":
        incoherent = out["date_sortie"].notna() & (out["date_sortie"] < out["date_entree"])
        for idx in out.index[incoherent & ~rejected]:
            report.add_error(excel_row[frame.index.get_loc(idx)], "date_sortie",
                             out.at[idx, "date_sortie"].date(),
                             "date de sortie antérieure à l'entrée (ligne rejetée)",
                             "exit_before_hire")
        rejected |= incoherent

    clean = out[~rejected].copy()
    if schema.key == "personnel":
        dup = clean["matricule"].duplicated(keep="last")
        if dup.any():
            report.warnings.append(
                f"{int(dup.sum())} matricule(s) en double : seule la dernière ligne est conservée."
            )
            clean = clean[~dup]

    report.rows_rejected = int(rejected.sum())
    report.rows_accepted = len(clean)
    if report.rows_accepted == 0:
        raise MappingError("Aucune ligne valide après contrôle : vérifiez la correspondance.")
    return clean.reset_index(drop=True), report
