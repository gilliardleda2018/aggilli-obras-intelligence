"""Users and license (MG Transportes model): login, lockout, temporary password, session revocation, admin rules,
and the 30-day license blocking the API while keeping sign-in and renewal reachable."""
import base64
import json
import time

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import license as lic
from app.db import Base, get_db
from app.main import app
from app.models import Membership, Organization
from app.users import create_user

SECRET = "x" * 48


@pytest.fixture()
def env(monkeypatch):
    monkeypatch.setenv("LOCAL_AUTH_SECRET", SECRET)
    monkeypatch.delenv("OBRAS_LICENSE_ENFORCE", raising=False)
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org = Organization(name="Grupo MG")
        db.add(org); db.flush()
        owner = create_user(db, "Dono@MG.com.br", "Dono", "SenhaInicial123", must_change=True)
        db.add(Membership(organization_id=org.id, subject_id=owner.id, role="OWNER")); db.commit()
        ids = {"org": org.id, "owner": owner.id}

    def get_test_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = get_test_db
    try:
        yield TestClient(app), ids
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def login(client, email, password, **extra):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password, **extra})


def auth(token):
    return {"Authorization": "Bearer " + token}


def test_login_change_password_and_revocation(env):
    client, ids = env
    assert login(client, "dono@mg.com.br", "errada").status_code == 401
    first = login(client, " DONO@mg.com.br ", "SenhaInicial123").json()
    assert first["must_change_password"] is True
    me = client.get("/api/v1/me", headers=auth(first["access_token"])).json()
    assert me["organizations"] == [{"id": ids["org"], "name": "Grupo MG", "role": "OWNER"}] and me["must_change_password"]
    weak = client.post("/api/v1/me/password", headers=auth(first["access_token"]),
                       json={"current_password": "SenhaInicial123", "new_password": "curta1"})
    assert weak.status_code == 422
    changed = client.post("/api/v1/me/password", headers=auth(first["access_token"]),
                          json={"current_password": "SenhaInicial123", "new_password": "NovaSenhaForte9"})
    assert changed.status_code == 200
    assert client.get("/api/v1/me", headers=auth(first["access_token"])).status_code == 401   # old session ended
    assert client.get("/api/v1/me", headers=auth(changed.json()["access_token"])).json()["must_change_password"] is False


def test_lockout_after_five_wrong_passwords(env):
    client, _ = env
    for _ in range(5):
        assert login(client, "dono@mg.com.br", "errada").status_code == 401
    assert login(client, "dono@mg.com.br", "SenhaInicial123").status_code == 423


def test_admin_manages_users(env):
    client, ids = env
    owner = auth(login(client, "dono@mg.com.br", "SenhaInicial123").json()["access_token"])
    base = f"/api/v1/organizations/{ids['org']}/users"
    added = client.post(base, headers=owner, json={"email": "eng@mg.com.br", "name": "Engenheira", "role": "ADMIN"}).json()
    temp = added["temporary_password"]
    assert added["must_change_password"] and len(temp) == 12
    assert client.post(base, headers=owner, json={"email": "eng@mg.com.br", "name": "Xavier", "role": "VIEWER"}).status_code == 409

    admin = auth(login(client, "eng@mg.com.br", temp).json()["access_token"])
    assert client.post(base, headers=admin, json={"email": "d2@mg.com.br", "name": "Outro dono", "role": "OWNER"}).status_code == 403
    viewer = client.post(base, headers=admin, json={"email": "ver@mg.com.br", "name": "Consulta", "role": "VIEWER"}).json()
    viewer_token = auth(login(client, "ver@mg.com.br", viewer["temporary_password"]).json()["access_token"])
    assert client.get(base, headers=viewer_token).status_code == 404                     # only managers see users
    assert {u["email"] for u in client.get(base, headers=admin).json()} == {"dono@mg.com.br", "eng@mg.com.br", "ver@mg.com.br"}

    assert client.patch(f"{base}/{viewer['user_id']}", headers=admin, json={"active": False}).json()["active"] is False
    assert client.get("/api/v1/me", headers=viewer_token).status_code == 401              # deactivated: session ends now
    assert login(client, "ver@mg.com.br", viewer["temporary_password"]).status_code == 401

    reset = client.post(f"{base}/{added['user_id']}/reset-password", headers=owner).json()
    assert client.get("/api/v1/me", headers=admin).status_code == 401                      # reset ends open sessions
    assert login(client, "eng@mg.com.br", reset["temporary_password"]).status_code == 200


def test_company_keeps_one_active_manager(env):
    client, ids = env
    owner = auth(login(client, "dono@mg.com.br", "SenhaInicial123").json()["access_token"])
    base = f"/api/v1/organizations/{ids['org']}/users"
    assert client.patch(f"{base}/{ids['owner']}", headers=owner, json={"role": "VIEWER"}).status_code == 409
    assert client.patch(f"{base}/{ids['owner']}", headers=owner, json={"active": False}).status_code == 409


def test_license_blocks_api_but_not_sign_in_or_renewal(env, monkeypatch):
    client, _ = env
    server = Ed25519PrivateKey.generate()
    public = base64.urlsafe_b64encode(server.public_key().public_bytes(serialization.Encoding.Raw,
                                                                       serialization.PublicFormat.Raw)).decode().rstrip("=")
    monkeypatch.setenv("OBRAS_LICENSE_ENFORCE", "1")
    monkeypatch.setenv("OBRAS_LICENSE_PUBLIC_KEY", public)
    monkeypatch.setenv("OBRAS_LICENSE_FARM_UID", "obras-grupo-mg")

    def fake_post(url, body, timeout):
        claims = {"iss": "Aggilli-Coletor", "version": 1, "device_id": body["device_id"], "public_key": body["public_key"],
                  "farm_uid": "obras-grupo-mg", "farm_name": "Grupo MG - Obras", "exp": int(time.time()) + 30 * 86400,
                  "license_id": "lic-1"}
        payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
        signature = base64.urlsafe_b64encode(server.sign(payload.encode())).decode().rstrip("=")
        return {"license": payload + "." + signature}
    monkeypatch.setattr(lic, "_post", fake_post)

    owner = auth(login(client, "dono@mg.com.br", "SenhaInicial123").json()["access_token"])
    assert client.get("/api/v1/projects", headers=owner).status_code == 402
    assert client.get("/api/v1/me", headers=owner).json()["license"]["state"] == "missing"
    assert client.post("/api/v1/license/activate", headers=owner, json={"code": "curto"}).status_code == 422
    done = client.post("/api/v1/license/activate", headers=owner, json={"code": "Código: ABCDEFGHIJKLMNOPQRSTUVWX"})
    assert done.status_code == 200, done.text
    assert done.json()["state"] == "active" and done.json()["days_left"] >= 29
    assert client.get("/api/v1/projects", headers=owner).status_code == 200
