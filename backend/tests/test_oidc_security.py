import os
import jwt
from fastapi.testclient import TestClient
from app.main import app
from app.security import require_identity

client=TestClient(app)

def test_unconfigured_provider_rejects_requests(monkeypatch):
    monkeypatch.delenv("OIDC_ISSUER",raising=False)
    monkeypatch.delenv("OIDC_AUDIENCE",raising=False)
    monkeypatch.delenv("OIDC_JWKS_URL",raising=False)
    assert client.get("/api/v1/projects").status_code==503

def test_missing_bearer_rejected_when_configured(monkeypatch):
    monkeypatch.setenv("OIDC_ISSUER","https://identity.example")
    monkeypatch.setenv("OIDC_AUDIENCE","obras-api")
    monkeypatch.setenv("OIDC_JWKS_URL","https://identity.example/jwks")
    assert client.get("/api/v1/projects").status_code==401

def test_unsigned_token_is_rejected(monkeypatch):
    monkeypatch.setenv("OIDC_ISSUER","https://identity.example")
    monkeypatch.setenv("OIDC_AUDIENCE","obras-api")
    monkeypatch.setenv("OIDC_JWKS_URL","https://identity.example/jwks")
    token=jwt.encode({"sub":"user","iss":"https://identity.example",
                      "aud":"obras-api","exp":9999999999,"iat":1700000000},
                     "attacker",algorithm="HS256")
    assert client.get("/api/v1/projects",headers={"Authorization":"Bearer "+token}).status_code==401
