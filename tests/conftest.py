"""Fixtures partagées : application isolée dans un dossier temporaire, jeux fictifs."""

from __future__ import annotations

import dataclasses
import io
from datetime import date

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.config import build_settings
from app.demo import generate_personnel
from app.factory import create_app

ADMIN_PASSWORD = "Admin-test-2026"
END = date(2026, 10, 31)


@pytest.fixture
def settings(tmp_path, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "t" * 48)
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", ADMIN_PASSWORD)
    monkeypatch.setenv("APP_ENV", "development")
    return dataclasses.replace(build_settings(), data_dir=tmp_path)


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as c:
        yield c


def login(client, username="admin", password=ADMIN_PASSWORD) -> dict:
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def admin_headers(client):
    return login(client)


@pytest.fixture(scope="session")
def personnel_frame() -> pd.DataFrame:
    return generate_personnel(300, end=END)



def xlsx_bytes(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_excel(buffer, index=False)
    return buffer.getvalue()


def import_dataset(client, headers, key: str, frame: pd.DataFrame) -> dict:
    up = client.post(f"/api/datasets/{key}/upload", headers=headers,
                     files={"file": (f"{key}.xlsx", xlsx_bytes(frame))})
    assert up.status_code == 200, up.text
    body = up.json()
    res = client.post(f"/api/datasets/{key}/confirm", headers=headers,
                      json={"upload_id": body["upload_id"], "mapping": body["mapping"]})
    assert res.status_code == 200, res.text
    return res.json()


@pytest.fixture
def loaded(client, admin_headers, personnel_frame):
    import_dataset(client, admin_headers, "personnel", personnel_frame)
    return client
