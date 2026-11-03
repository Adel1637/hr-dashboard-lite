"""Dépendances FastAPI : état partagé et utilisateur connecté.

Toute route protégée déclare `Depends(current_user)` : le contrôle se fait côté
serveur, quel que soit ce que l'interface affiche ou masque.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.security.tokens import TokenError, decode_token
from app.security.users import User
from app.state import KitState

_bearer = HTTPBearer(auto_error=False)


def get_state(request: Request) -> KitState:
    return request.app.state.kit


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    state: KitState = Depends(get_state),
) -> User:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentification requise",
                                 headers={"WWW-Authenticate": "Bearer"})
    if creds is None or creds.scheme.lower() != "bearer":
        raise unauthorized
    try:
        payload = decode_token(creds.credentials, state.settings.jwt_secret)
    except TokenError as exc:
        unauthorized.detail = "Session expirée" if str(exc) == "expired" else "Jeton invalide"
        raise unauthorized from exc
    user = state.users.get(payload["sub"])
    if user is None or payload.get("ver") != user.token_version:
        raise unauthorized
    return user
