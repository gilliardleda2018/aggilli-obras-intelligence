"""Work diary photos: integrity hash, EXIF vs device location, on-site check, access control and the day-by-day diary."""
import io
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import FieldReport, Membership, Organization, Project, ServiceItem
from app.security import require_identity

SITE = (-5.258123, -44.648988)


def jpeg(color=(200, 120, 40), gps: tuple[float, float] | None = None, taken: str | None = None) -> bytes:
    image = Image.new("RGB", (64, 48), color)
    exif = Image.Exif()
    if gps:
        def dms(value):
            value = abs(value); d = int(value); m = int((value - d) * 60); s = round(((value - d) * 60 - m) * 60, 4)
            return (d, m, s)
        exif[0x8825] = {1: "S" if gps[0] < 0 else "N", 2: dms(gps[0]), 3: "W" if gps[1] < 0 else "E", 4: dms(gps[1])}
    if taken:
        exif.get_ifd(0x8769)[36867] = taken
    out = io.BytesIO()
    image.save(out, "JPEG", exif=exif)
    return out.getvalue()


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("PHOTO_STORAGE_DIR", str(tmp_path))
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org, other = Organization(name="Construtora"), Organization(name="Outra")
        db.add_all([org, other]); db.flush()
        db.add_all([Membership(organization_id=org.id, subject_id="campo", role="FIELD_OPERATOR"),
                    Membership(organization_id=org.id, subject_id="viewer", role="VIEWER"),
                    Membership(organization_id=other.id, subject_id="outsider", role="OWNER")])
        project = Project(organization_id=org.id, name="Escola", location="Tuntum", latitude=Decimal(str(SITE[0])), longitude=Decimal(str(SITE[1])))
        unlocated = Project(organization_id=org.id, name="Posto", location="Tuntum")
        db.add_all([project, unlocated]); db.flush()
        service = ServiceItem(project_id=project.id, name="Alvenaria", unit="m2", planned_quantity=Decimal(100), weight=Decimal(40))
        db.add(service); db.flush()
        report = FieldReport(project_id=project.id, report_date=date(2026, 10, 14), weather="Sol", summary="Levantadas paredes", recorded_by="campo")
        db.add(report); db.commit()
        ids = {"pid": project.id, "unlocated": unlocated.id, "service": service.id, "report": report.id}

    def get_test_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = get_test_db
    who = {"sub": "campo"}
    app.dependency_overrides[require_identity] = lambda: who["sub"]
    try:
        yield TestClient(app), ids, who, tmp_path
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def send(client, pid, data: bytes, **form):
    return client.post(f"/api/v1/projects/{pid}/photos", files={"file": ("foto.jpg", data, "image/jpeg")},
                       data={k: str(v) for k, v in form.items()})


def test_device_location_on_site_with_hash_and_original_file(env):
    client, ids, _, folder = env
    data = jpeg()
    response = send(client, ids["pid"], data, latitude=-5.2590, longitude=-44.6490, accuracy=12, report_id=ids["report"],
                    service_id=ids["service"], caption="Parede norte", taken_at="2026-10-14T09:30:00")
    assert response.status_code == 201, response.text
    photo = response.json()
    assert photo["location_source"] == "DEVICE" and photo["place"] == "NA_OBRA" and photo["distance_m"] < 300
    assert photo["service"] == "Alvenaria" and photo["taken_at_source"] == "DEVICE" and photo["taken_at"].endswith("-03:00")
    import hashlib
    assert photo["sha256"] == hashlib.sha256(data).hexdigest()
    assert (folder / (photo["id"] + ".jpg")).read_bytes() == data  # original kept untouched
    file = client.get("/api/v1" + photo["url"])
    assert file.status_code == 200 and file.content == data and file.headers["content-type"] == "image/jpeg"


def test_exif_gps_and_time_win_over_device(env):
    client, ids, _, _ = env
    far = (-5.30, -44.70)  # ~7 km away: the camera says where the picture really was taken
    photo = send(client, ids["pid"], jpeg(gps=far, taken="2026:10:13 16:05:00"), latitude=SITE[0], longitude=SITE[1]).json()
    assert photo["location_source"] == "EXIF" and photo["place"] == "FORA_DA_OBRA" and photo["distance_m"] > 5000
    assert abs(photo["latitude"] - far[0]) < 1e-4 and photo["taken_at"] == "2026-10-13T16:05:00-03:00"
    assert photo["accuracy_m"] is None


def test_no_location_is_never_guessed(env):
    client, ids, _, _ = env
    assert send(client, ids["pid"], jpeg()).json()["place"] == "SEM_LOCALIZACAO"
    assert send(client, ids["unlocated"], jpeg(), latitude=SITE[0], longitude=SITE[1]).json()["place"] == "OBRA_SEM_LOCAL"


def test_validation(env):
    client, ids, _, _ = env
    assert send(client, ids["pid"], b"not an image").status_code == 415
    assert send(client, ids["pid"], jpeg(), latitude=48.85, longitude=2.35).status_code == 422          # outside Brazil
    assert send(client, ids["pid"], jpeg(), latitude=SITE[0]).status_code == 422                        # both or none
    assert send(client, ids["unlocated"], jpeg(), report_id=ids["report"]).status_code == 422           # report of another project
    assert send(client, ids["pid"], jpeg(), service_id="x" * 36).status_code == 422
    data = jpeg((1, 2, 3))
    assert send(client, ids["pid"], data).status_code == 201
    assert send(client, ids["pid"], data).status_code == 409                                             # same file twice


def test_access_control(env):
    client, ids, who, _ = env
    photo = send(client, ids["pid"], jpeg()).json()
    who["sub"] = "viewer"
    assert send(client, ids["pid"], jpeg((9, 9, 9))).status_code == 404       # viewers cannot add photos
    assert client.get("/api/v1" + photo["url"]).status_code == 200
    who["sub"] = "outsider"
    assert client.get("/api/v1" + photo["url"]).status_code == 404
    assert client.get(f"/api/v1/projects/{ids['pid']}/diary").status_code == 404


def test_diary_groups_by_day_and_filters_by_stage(env):
    client, ids, _, _ = env
    send(client, ids["pid"], jpeg((10, 10, 10)), report_id=ids["report"], service_id=ids["service"])
    send(client, ids["pid"], jpeg((20, 20, 20), taken="2026:10:12 08:00:00"))
    body = client.get(f"/api/v1/projects/{ids['pid']}/diary").json()
    assert [day["date"] for day in body["days"]] == ["2026-10-14", "2026-10-12"]
    assert body["days"][0]["reports"][0]["summary"] == "Levantadas paredes" and len(body["days"][0]["photos"]) == 1
    assert body["services"] == [{"id": ids["service"], "name": "Alvenaria"}] and body["project"]["located"] is True
    stage = client.get(f"/api/v1/projects/{ids['pid']}/photos", params={"service_id": ids["service"]}).json()
    assert len(stage) == 1 and stage[0]["service"] == "Alvenaria"
