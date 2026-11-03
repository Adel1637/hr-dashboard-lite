"""Lecture des fichiers Excel et CSV importés.

- Contrôle du type et de la taille du fichier avant toute lecture.
- Détection automatique de la ligne d'en-tête (titres ou lignes vides au-dessus).
- CSV : détection du séparateur et de l'encodage.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass

import pandas as pd

ALLOWED_EXTENSIONS = (".xlsx", ".csv")
MAX_ROWS = 500_000
_HEADER_SCAN_ROWS = 15


class ImportError_(ValueError):
    """Erreur lisible par l'utilisateur lors d'un import."""


@dataclass
class RawTable:
    frame: pd.DataFrame
    sheets: list[str]
    sheet: str | None
    header_row: int  # index 0 de la ligne d'en-tête dans le fichier


def _extension(filename: str) -> str:
    name = filename.lower().strip()
    for ext in ALLOWED_EXTENSIONS:
        if name.endswith(ext):
            return ext
    raise ImportError_("Format non pris en charge : utilisez un fichier .xlsx ou .csv.")


def _find_header_row(raw: pd.DataFrame) -> int:
    """Première ligne majoritairement textuelle et remplie : c'est l'en-tête."""
    width = raw.shape[1]
    for idx in range(min(_HEADER_SCAN_ROWS, len(raw))):
        row = raw.iloc[idx]
        filled = row.dropna()
        texts = [v for v in filled if isinstance(v, str) and v.strip()]
        if width and len(filled) >= max(2, width * 0.5) and len(texts) >= len(filled) * 0.8:
            return idx
    return 0


def _apply_header(raw: pd.DataFrame, header_row: int) -> pd.DataFrame:
    header = [
        str(v).strip() if pd.notna(v) and str(v).strip() else f"Colonne {i + 1}"
        for i, v in enumerate(raw.iloc[header_row])
    ]
    seen: dict[str, int] = {}
    unique = []
    for name in header:
        count = seen.get(name, 0)
        unique.append(name if count == 0 else f"{name} ({count + 1})")
        seen[name] = count + 1
    frame = raw.iloc[header_row + 1:].copy()
    frame.columns = unique
    frame = frame.dropna(how="all")
    # Colonnes entièrement vides et sans nom : on les retire.
    empty = [c for c in frame.columns if c.startswith("Colonne ") and frame[c].isna().all()]
    return frame.drop(columns=empty).reset_index(drop=True)


def _read_csv(content: bytes) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:  # pragma: no cover - latin-1 décode toujours
        raise ImportError_("Encodage du fichier CSV non reconnu.")
    sample = text[:20_000]
    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters=";,\t|").delimiter
    except csv.Error:
        delimiter = ";" if sample.count(";") > sample.count(",") else ","
    return pd.read_csv(io.StringIO(text), sep=delimiter, header=None, dtype=object,
                       skip_blank_lines=False)


def read_table(content: bytes, filename: str, sheet: str | None = None,
               max_bytes: int | None = None) -> RawTable:
    if not content:
        raise ImportError_("Le fichier est vide.")
    if max_bytes is not None and len(content) > max_bytes:
        raise ImportError_(f"Fichier trop volumineux (maximum {max_bytes // (1024 * 1024)} Mo).")

    ext = _extension(filename)
    sheets: list[str] = []
    try:
        if ext == ".csv":
            raw = _read_csv(content)
            chosen = None
        else:
            if not content.startswith(b"PK"):
                raise ImportError_("Le fichier n'est pas un classeur Excel .xlsx valide.")
            book = pd.ExcelFile(io.BytesIO(content), engine="openpyxl")
            sheets = list(book.sheet_names)
            chosen = sheet if sheet in sheets else sheets[0]
            raw = book.parse(chosen, header=None, dtype=object)
    except ImportError_:
        raise
    except Exception as exc:  # fichier corrompu, format inattendu…
        raise ImportError_(f"Lecture impossible : {exc.__class__.__name__}.") from exc

    raw = raw.dropna(how="all").reset_index(drop=True)
    if raw.empty:
        raise ImportError_("Aucune donnée trouvée dans le fichier.")
    header_row = _find_header_row(raw)
    frame = _apply_header(raw, header_row)
    if frame.empty:
        raise ImportError_("Le fichier ne contient qu'une ligne d'en-tête.")
    if len(frame) > MAX_ROWS:
        raise ImportError_(f"Trop de lignes (maximum {MAX_ROWS:,}).".replace(",", " "))
    return RawTable(frame=frame, sheets=sheets, sheet=chosen, header_row=header_row)
