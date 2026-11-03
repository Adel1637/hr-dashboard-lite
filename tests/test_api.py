"""Tests de l'API Lite : sécurité, import, module Effectifs, tableau de données."""

import json

import pytest

from tests.conftest import ADMIN_PASSWORD, import_dataset, xlsx_bytes


def test_health_and_public_config_without_auth(client):
    assert client.get("/api/health").json()["status"] == "ok"
    config = client.get("/api/config").json()
    assert config["edition"] == "lite"
    assert config["accent"].startswith("#")
    assert "secret" not in json.dumps(config).lower()


def test_security_headers(client):
    res = client.get("/api/health")
    assert res.headers["x-frame-options"] == "DENY"
    assert "default-src 'self'" in res.headers["content-security-policy"]


@pytest.mark.parametrize("path", ["/api/meta", "/api/modules/effectifs", "/api/data/personnel"])
def test_routes_require_a_token(client, path):
    assert client.get(path).status_code == 401


def test_forged_token_is_refused(client):
    import jwt
    forged = jwt.encode({"sub": "admin", "ver": 0, "iat": 0, "exp": 9999999999},
                        "w" * 48, algorithm="HS256")
    assert client.get("/api/meta", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_wrong_password_and_rate_limit(client):
    for _ in range(5):
        assert client.post("/api/auth/login",
                           json={"username": "admin", "password": "nope"}).status_code == 401
    assert client.post("/api/auth/login",
                       json={"username": "admin", "password": ADMIN_PASSWORD}).status_code == 429


def test_password_change_revokes_old_tokens(client, admin_headers):
    res = client.post("/api/auth/password", headers=admin_headers,
                      json={"current_password": ADMIN_PASSWORD, "new_password": "Nouveau-2026!"})
    assert res.status_code == 200
    assert client.get("/api/meta", headers=admin_headers).status_code == 401


def test_import_flow_and_mapping_reuse(client, admin_headers, personnel_frame):
    result = import_dataset(client, admin_headers, "personnel", personnel_frame)
    assert result["report"]["rows_accepted"] == len(personnel_frame)
    again = client.post("/api/datasets/personnel/upload", headers=admin_headers,
                        files={"file": ("p.xlsx", xlsx_bytes(personnel_frame))}).json()
    assert again["mapping_reused"] is True


def test_only_personnel_dataset_exists(client, admin_headers, personnel_frame):
    res = client.post("/api/datasets/formation/upload", headers=admin_headers,
                      files={"file": ("f.xlsx", xlsx_bytes(personnel_frame))})
    assert res.status_code == 404


def test_effectifs_module_and_cache_invalidation(loaded, admin_headers, personnel_frame):
    params = {"ref_date": "2026-10-31", "months": 12}
    first = loaded.get("/api/modules/effectifs", headers=admin_headers, params=params).json()
    assert first["kpis"] and first["charts"]
    import_dataset(loaded, admin_headers, "personnel", personnel_frame.head(100))
    second = loaded.get("/api/modules/effectifs", headers=admin_headers, params=params).json()
    assert second["kpis"][0]["value"] < first["kpis"][0]["value"]


def test_filters_apply(loaded, admin_headers):
    base = {"ref_date": "2026-10-31", "lang": "en"}
    everyone = loaded.get("/api/modules/effectifs", headers=admin_headers, params=base).json()
    north = loaded.get("/api/modules/effectifs", headers=admin_headers,
                       params={**base, "site": ["Site Nord"]}).json()
    assert 0 < north["kpis"][0]["value"] < everyone["kpis"][0]["value"]


@pytest.mark.parametrize("module", ["mouvements", "demographie", "formation"])
def test_pro_modules_are_announced_but_locked(loaded, admin_headers, module):
    meta = loaded.get("/api/meta", headers=admin_headers).json()
    entry = next(m for m in meta["modules"] if m["key"] == module)
    assert entry["pro"] is True and entry["ready"] is False
    res = loaded.get(f"/api/modules/{module}", headers=admin_headers)
    assert res.status_code == 409
    assert "Pro" in res.json()["detail"]


def test_pro_hints_can_be_disabled(settings, monkeypatch):
    import dataclasses

    from fastapi.testclient import TestClient

    from app.factory import create_app
    from tests.conftest import login

    with TestClient(create_app(dataclasses.replace(settings, show_pro_hints=False))) as c:
        meta = c.get("/api/meta", headers=login(c)).json()
        assert [m["key"] for m in meta["modules"]] == ["effectifs"]
        assert c.get("/api/config").json()["show_pro_hints"] is False


def test_table_search_sort_and_pagination(loaded, admin_headers):
    res = loaded.get("/api/data/personnel", headers=admin_headers, params={
        "q": "site nord", "sort": "date_entree", "order": "desc", "size": 10}).json()
    assert res["total"] > 0 and len(res["rows"]) <= 10
    assert all(r["site"] == "Site Nord" for r in res["rows"])
    dates = [r["date_entree"] for r in res["rows"]]
    assert dates == sorted(dates, reverse=True)


def test_no_export_or_admin_routes_in_lite(loaded, admin_headers):
    assert loaded.post("/api/data/personnel/export", headers=admin_headers,
                       json={"format": "csv"}).status_code in (404, 405)
    assert loaded.get("/api/admin/users", headers=admin_headers).status_code == 404


def test_production_refuses_missing_secret(monkeypatch):
    from app.config import build_settings
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "")
    with pytest.raises(RuntimeError):
        build_settings()
