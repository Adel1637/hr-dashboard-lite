"""Connexion, déconnexion, profil et changement de mot de passe."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.api.deps import client_ip, current_user, get_state
from app.security.tokens import create_token
from app.security.users import User, UserError
from app.state import KitState

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str = Field(max_length=40)
    password: str = Field(max_length=200)


class PasswordIn(BaseModel):
    current_password: str = Field(max_length=200)
    new_password: str = Field(max_length=200)


def _profile(user: User) -> dict:
    return user.public()


@router.post("/login")
def login(body: LoginIn, request: Request, state: KitState = Depends(get_state)) -> dict:
    ip = client_ip(request)
    if not state.limiter.hit(f"login:{ip}", state.settings.rate_limit_login):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Trop de tentatives, réessayez dans une minute.")
    user = state.users.authenticate(body.username, body.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Identifiants incorrects")
    token, expires_in = create_token(user.username, user.role, user.token_version,
                                     state.settings.jwt_secret,
                                     state.settings.jwt_expire_minutes)
    return {"access_token": token, "token_type": "bearer", "expires_in": expires_in,
            "user": _profile(user)}


@router.post("/logout")
def logout(user: User = Depends(current_user)) -> dict:
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user)) -> dict:
    return _profile(user)


@router.post("/password")
def change_password(body: PasswordIn, user: User = Depends(current_user),
                    state: KitState = Depends(get_state)) -> dict:
    if state.users.authenticate(user.username, body.current_password) is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mot de passe actuel incorrect")
    try:
        state.users.change_password(user.username, body.new_password)
    except UserError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {"ok": True}
