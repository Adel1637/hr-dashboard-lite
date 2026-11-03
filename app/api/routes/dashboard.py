"""Configuration publique, état des données et calcul des modules."""

from __future__ import annotations

from datetime import date

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import current_user, get_state
from app.core.analytics import ModuleUnavailable
from app.core.filters import FILTER_COLUMNS, Filters, filter_options
from app.schemas import SCHEMAS
from app.security.users import User
from app.state import KitState

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/config")
def public_config(state: KitState = Depends(get_state)) -> dict:
    """Identité et réglages visuels : lisible sans connexion (page de login)."""
    return state.settings.public()


@router.get("/meta")
def meta(user: User = Depends(current_user), state: KitState = Depends(get_state)) -> dict:
    personnel = state.store.get("personnel")
    last_event = None
    if personnel is not None:
        last_event = max(personnel["date_entree"].max(),
                         personnel["date_sortie"].max()
                         if personnel["date_sortie"].notna().any() else pd.NaT)
    return {
        "datasets": state.store.meta(),
        "modules": state.analytics.available_modules(),
        "filters": filter_options(personnel),
        "suggested_ref_date": (last_event.date().isoformat() if pd.notna(last_event)
                               else date.today().isoformat()),
        "schemas": {k: [{"key": f.key, "type": f.type, "required": f.required}
                        for f in s.fields] for k, s in SCHEMAS.items()},
    }


@router.get("/modules/{key}")
def module_data(
    key: str,
    ref_date: date | None = None,
    months: int = Query(12, ge=1, le=60),
    lang: str = Query("fr", pattern="^(fr|en)$"),
    site: list[str] = Query(default=[]),
    service: list[str] = Query(default=[]),
    categorie: list[str] = Query(default=[]),
    type_contrat: list[str] = Query(default=[]),
    sexe: list[str] = Query(default=[]),
    user: User = Depends(current_user),
    state: KitState = Depends(get_state),
) -> dict:
    raw = dict(zip(FILTER_COLUMNS, (site, service, categorie, type_contrat, sexe), strict=True))
    filters = Filters.build(ref_date or date.today(), months, raw)
    try:
        return state.analytics.run(key, filters, lang)
    except ModuleUnavailable as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
