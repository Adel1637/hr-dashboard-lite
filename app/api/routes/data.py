"""Tableau de données : recherche, tri et pagination côté serveur.

La version Pro ajoute les filtres par colonne, les colonnes épinglées, les vues
enregistrées, la sélection multiple et les exports CSV / Excel.
"""

from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import current_user, get_state
from app.schemas import SCHEMAS
from app.security.users import User
from app.state import KitState

router = APIRouter(prefix="/api/data", tags=["data"])
MAX_PAGE_SIZE = 200


def _as_text(frame: pd.DataFrame) -> pd.DataFrame:
    """Représentation texte utilisée pour la recherche et l'affichage."""
    out = pd.DataFrame(index=frame.index)
    for col in frame.columns:
        series = frame[col]
        if pd.api.types.is_datetime64_any_dtype(series):
            out[col] = series.dt.strftime("%Y-%m-%d")
        else:
            values = series.astype(object).where(series.notna(), None)
            out[col] = values.map(lambda v: None if v is None else
                                  (f"{v:g}" if isinstance(v, float) else str(v)))
    return out


@router.get("/{key}")
def table(key: str, page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
          q: str = Query("", max_length=200), sort: str | None = None,
          order: str = Query("asc", pattern="^(asc|desc)$"),
          user: User = Depends(current_user), state: KitState = Depends(get_state)) -> dict:
    if key not in SCHEMAS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Jeu de données inconnu")
    frame = state.store.get(key)
    if frame is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Aucune donnée importée")

    result = frame
    if q.strip():
        text = _as_text(frame)
        needle = q.strip().lower()
        hit = pd.Series(False, index=frame.index)
        for col in text.columns:
            hit |= text[col].fillna("").str.lower().str.contains(needle, regex=False)
        result = frame[hit]
    if sort in frame.columns:
        result = result.sort_values(sort, ascending=order == "asc", na_position="last",
                                    kind="mergesort")

    start = (page - 1) * size
    chunk = _as_text(result.iloc[start:start + size])
    return {
        "columns": [{"key": f.key, "type": f.type} for f in SCHEMAS[key].fields],
        "rows": chunk.to_dict(orient="records"),
        "total": len(result),
        "page": page,
        "size": size,
    }
