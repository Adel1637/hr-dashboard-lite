"""Import en deux étapes : lecture du fichier, puis validation de la correspondance."""

from __future__ import annotations

from datetime import datetime, time

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel

from app.api.deps import client_ip, current_user, get_state
from app.core.importer import ImportError_, read_table
from app.core.mapping import MappingError, apply_mapping, columns_signature, suggest_mapping
from app.schemas import SCHEMAS
from app.security.users import User
from app.state import KitState, PendingUpload, pending_expiry

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


class ConfirmIn(BaseModel):
    upload_id: str
    mapping: dict[str, str | None]


def _schema(key: str):
    if key not in SCHEMAS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Jeu de données inconnu")
    return SCHEMAS[key]


def _cell(value) -> str:
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return ""
    if isinstance(value, datetime):  # dates Excel : on masque l'heure si elle est vide
        return value.date().isoformat() if value.time() == time(0) else value.isoformat(" ")
    return str(value)[:60]


def _preview(frame: pd.DataFrame, rows: int = 5) -> list[list[str]]:
    return [[_cell(v) for v in row] for row in frame.head(rows).itertuples(index=False)]


@router.post("/{key}/upload")
async def upload(key: str, request: Request, file: UploadFile = File(...),
                 sheet: str | None = Form(None), user: User = Depends(current_user),
                 state: KitState = Depends(get_state)) -> dict:
    schema = _schema(key)
    ip = client_ip(request)
    if not state.limiter.hit(f"upload:{ip}", state.settings.rate_limit_upload):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Trop d'imports, patientez.")

    limit = state.settings.max_upload_bytes
    content = await file.read(limit + 1)
    try:
        table = read_table(content, file.filename or "", sheet=sheet, max_bytes=limit)
    except ImportError_ as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    columns = [str(c) for c in table.frame.columns]
    signature = columns_signature(columns)
    saved = state.store.saved_mapping(key, signature)
    mapping = saved if saved and all(v in columns for v in saved.values() if v) else None
    upload_id = state.add_pending(PendingUpload(
        dataset=key, table=table, filename=file.filename or "", signature=signature,
        user=user.username, expires=pending_expiry()))

    return {
        "upload_id": upload_id,
        "filename": file.filename,
        "sheets": table.sheets,
        "sheet": table.sheet,
        "rows": len(table.frame),
        "columns": columns,
        "preview": _preview(table.frame),
        "mapping": mapping or suggest_mapping(columns, schema),
        "mapping_reused": mapping is not None,
        "fields": [{"key": f.key, "type": f.type, "required": f.required}
                   for f in schema.fields],
    }


@router.post("/{key}/confirm")
def confirm(key: str, body: ConfirmIn, user: User = Depends(current_user),
            state: KitState = Depends(get_state)) -> dict:
    schema = _schema(key)
    pending = state.peek_pending(body.upload_id, user.username)
    if pending is None or pending.dataset != key:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            "Import expiré ou introuvable : déposez à nouveau le fichier.")
    mapping = {f.key: body.mapping.get(f.key) or None for f in schema.fields}
    try:
        frame, report = apply_mapping(pending.table.frame, schema, mapping,
                                      pending.table.header_row)
    except MappingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    state.pop_pending(body.upload_id, user.username)
    state.store.save(key, frame, filename=pending.filename, user=user.username,
                     mapping=mapping, signature=pending.signature)
    state.analytics.invalidate()
    return {"report": report.as_dict(), "meta": state.store.meta()[key]}
