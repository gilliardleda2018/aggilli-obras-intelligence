"""Maps: geocoding candidates with checks, confirmed locations with provenance, 30-day refresh and the portfolio map."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import geo
from app.db import Base, get_db
from app.main import app
from app.models import Membership, Organization, Project
from app.security import require_identity

GOOGLE = {"status": "OK", "results": [
    {"formatted_address": "R. Principal, 100 - Centro, Tuntum - MA", "place_id": "place-rooftop", "partial_match": False,
     "geometry": {"location": {"lat": -5.2581234, "lng": -44.6489876}, "location_type": "ROOFTOP"}, "types": ["street_address"],
     "address_components": [{"long_name": "Tuntum", "short_name": "Tuntum", "types": ["administrative_area_level_2", "political"]},
                            {"long_name": "Maranhão", "short_name": "MA", "types": ["administrative_area_level_1", "political"]}]},
    {"formatted_address": "Presidente Dutra - MA", "place_id": "place-city", "partial_match": True,
     "geometry": {"location": {"lat": -5.29, "lng": -44.49}, "location_type": "APPROXIMATE"}, "types": ["locality"],
     "address_components": [{"long_name": "Presidente Dutra", "short_name": "Presidente Dutra", "types": ["locality", "political"]}]},
]}


@pytest.fixture()
def env(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org, other = Organization(name="Construtora"), Organization(name="Outra")
        db.add_all([org, other]); db.flush()
        db.add_all([Membership(organization_id=org.id, subject_id="eng", role="ENGINEER"),
                    Membership(organization_id=org.id, subject_id="viewer", role="VIEWER"),
                    Membership(organization_id=other.id, subject_id="outsider", role="OWNER")])
        project = Project(organization_id=org.id, name="Escola", location="Tuntum", municipality="Tuntum", address="Rua Principal, 100")
        pool = Project(organization_id=org.id, name="Despesas gerais", location="-", status="COST_POOL")
        db.add_all([project, pool]); db.commit()
        pid = project.id

    def get_test_db():
        with Session(engine) as session:
            yield session

    calls = []
    monkeypatch.setattr(geo, "_call_geocoding", lambda params: calls.append(params) or GOOGLE)
    app.dependency_overrides[get_db] = get_test_db
    who = {"sub": "eng"}
    app.dependency_overrides[require_identity] = lambda: who["sub"]
    try:
        yield TestClient(app), engine, pid, who, calls
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_geocode_returns_checked_candidates_without_saving(env):
    client, engine, pid, _, calls = env
    body = client.post(f"/api/v1/projects/{pid}/geocode", json={}).json()
    assert body["query"] == "Rua Principal, 100, Tuntum" and calls[0]["components"] == "country:BR"
    best, city = body["candidates"]
    assert best["warnings"] == [] and best["latitude"] == -5.258123 and best["state"] == "MA"
    assert "correspondência parcial do endereço" in city["warnings"] and any("difere do cadastrado" in w for w in city["warnings"])
    assert any("aproximado" in w for w in city["warnings"])
    with Session(engine) as db:
        assert db.get(Project, pid).latitude is None  # a candidate is never persisted on its own


def test_confirm_location_with_provenance_and_validation(env):
    client, engine, pid, who, _ = env
    put = lambda body: client.put(f"/api/v1/projects/{pid}/location", json=body)  # noqa: E731
    assert put({"latitude": -5.258123, "longitude": -44.648988, "source": "GEOCODED"}).status_code == 422   # place id required
    assert put({"latitude": 48.85, "longitude": 2.35, "source": "MAP"}).status_code == 422                 # outside Brazil
    assert put({"latitude": -5.25, "source": "MAP"}).status_code == 422                                    # both or none
    saved = put({"latitude": -5.258123, "longitude": -44.648988, "source": "GEOCODED", "accuracy": "ROOFTOP", "place_id": "place-rooftop"})
    assert saved.status_code == 200
    location = saved.json()["location"]
    assert location["source"] == "GEOCODED" and location["confirmed_by"] == "eng" and location["refresh_due"] is False
    moved = put({"latitude": -5.2583, "longitude": -44.6491, "source": "MAP"}).json()["location"]
    assert moved["source"] == "MAP" and moved["place_id"] is None  # pin adjusted by a person: own data, no Google cache
    who["sub"] = "viewer"
    assert put({"latitude": -5.2, "longitude": -44.6, "source": "MAP"}).status_code == 404
    assert client.post(f"/api/v1/projects/{pid}/geocode", json={}).status_code == 404
    assert client.get(f"/api/v1/projects/{pid}/location").json()["can_edit"] is False
    who["sub"] = "outsider"
    assert client.get(f"/api/v1/projects/{pid}/location").status_code == 404
    who["sub"] = "eng"
    assert put({}).json()["location"]["source"] is None  # clearing removes provenance too


def test_typed_coordinates_are_manual(env):
    client, _, pid, _, _ = env
    assert client.patch(f"/api/v1/projects/{pid}", json={"latitude": "-5.2591", "longitude": "-44.6489"}).status_code == 200
    location = client.get(f"/api/v1/projects/{pid}/location").json()["location"]
    assert location["source"] == "MANUAL" and location["confirmed_by"] == "eng"


def test_geocoded_coordinates_refresh_after_30_days(env):
    client, engine, pid, _, calls = env
    client.put(f"/api/v1/projects/{pid}/location", json={"latitude": -5.2, "longitude": -44.6, "source": "GEOCODED", "place_id": "place-rooftop"})
    assert client.post("/api/v1/geo/refresh").json() == {"refreshed": [], "removed": []}
    with Session(engine) as db:
        db.get(Project, pid).location_confirmed_at = datetime.now(timezone.utc) - timedelta(days=31)
        db.commit()
    assert client.get(f"/api/v1/projects/{pid}/location").json()["location"]["refresh_due"] is True
    assert client.post("/api/v1/geo/refresh").json()["refreshed"] == [pid]
    assert calls[-1] == {"place_id": "place-rooftop"}
    with Session(engine) as db:
        assert db.get(Project, pid).latitude == Decimal("-5.258123")


def test_map_lists_authorized_works_with_risk(env, monkeypatch):
    client, _, pid, who, _ = env
    monkeypatch.delenv("GOOGLE_MAPS_SERVER_KEY", raising=False)
    body = client.get("/api/v1/map/projects").json()
    assert [p["name"] for p in body["projects"]] == ["Escola"] and body["maps_configured"] is False  # cost pools are not places
    work = body["projects"][0]
    assert work["organization"] == "Construtora" and work["risk"]["level"] == "sem_dados" and work["location"]["latitude"] is None
    who["sub"] = "outsider"
    assert client.get("/api/v1/map/projects").json()["projects"] == []


def test_risk_classes():
    ok = {"status": "ok"}
    assert geo.risk({**ok, "probability_on_time": 0.9}, {**ok, "budget": 100, "eac_p50": 99}, "IN_PROGRESS")["level"] == "baixo"
    assert geo.risk({**ok, "probability_on_time": 0.5}, {**ok, "budget": 100, "eac_p50": 99}, "IN_PROGRESS")["level"] == "medio"
    high = geo.risk({**ok, "probability_on_time": 0.5}, {**ok, "budget": 100, "eac_p50": 110}, "IN_PROGRESS")
    assert high["level"] == "alto" and len(high["reasons"]) == 2
    assert geo.risk({}, {}, "DONE")["level"] == "concluida"


def test_geocoding_requires_server_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_SERVER_KEY", raising=False)
    with pytest.raises(Exception) as error:
        geo._call_geocoding({"address": "x"})
    assert getattr(error.value, "status_code", None) == 503
