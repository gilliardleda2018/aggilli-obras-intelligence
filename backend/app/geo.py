"""Maps: geocoding with human confirmation, location provenance and the portfolio map (status, progress and risk).

Google Maps Platform terms: geocoded latitude/longitude may be cached for at most 30 days, while place IDs may be kept.
GEOCODED locations therefore store the place ID and are refreshed (or flagged) after 30 days. Coordinates placed by a
person on the map, captured on site or typed in are the organization's own data. Coordinates are never guessed: a
geocoding result is only a candidate until someone confirms it.
"""
import json
import os
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .intelligence import project_intelligence
from .measurements import access
from .models import AuditEvent, Membership, Organization, Project
from .security import require_identity

router = APIRouter(prefix="/api/v1", tags=["maps"])
READ_ROLES = ["OWNER", "ADMIN", "ENGINEER", "INSPECTOR", "FIELD_OPERATOR", "VIEWER"]
EDIT_ROLES = ["OWNER", "ADMIN", "ENGINEER"]
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
CACHE_DAYS = 30
BRAZIL = (-34.0, 5.5, -74.1, -34.7)   # lat min, lat max, lon min, lon max
SOURCES = ("GEOCODED", "MAP", "FIELD", "MANUAL")


def _norm(text: str | None) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", (text or "").lower()) if unicodedata.category(c) != "Mn").strip()


def _in_brazil(lat: float, lon: float) -> bool:
    return BRAZIL[0] <= lat <= BRAZIL[1] and BRAZIL[2] <= lon <= BRAZIL[3]


def _call_geocoding(params: dict) -> dict:
    key = os.getenv("GOOGLE_MAPS_SERVER_KEY", "")
    if not key:
        raise HTTPException(status_code=503, detail="Geocoding is not configured (GOOGLE_MAPS_SERVER_KEY)")
    query = urllib.parse.urlencode({**params, "key": key, "language": "pt-BR", "region": "br"})
    try:
        with urllib.request.urlopen(GEOCODE_URL + "?" + query, timeout=10) as response:  # noqa: S310 - fixed https URL
            data = json.load(response)
    except Exception as exc:  # network failure, timeout
        raise HTTPException(status_code=502, detail="Geocoding service unavailable") from exc
    status = data.get("status")
    if status in ("OK", "ZERO_RESULTS"):
        return data
    if status == "OVER_QUERY_LIMIT":
        raise HTTPException(status_code=429, detail="Geocoding quota exceeded")
    raise HTTPException(status_code=502, detail=f"Geocoding error: {status}")


def candidates(data: dict, municipality: str | None) -> list[dict]:
    """Turns a Geocoding response into candidates with the checks a person needs before confirming one."""
    rows = []
    for result in data.get("results", [])[:5]:
        location = result.get("geometry", {}).get("location", {})
        lat, lon = location.get("lat"), location.get("lng")
        if lat is None or lon is None:
            continue
        components = result.get("address_components", [])
        city = next((c["long_name"] for c in components if "administrative_area_level_2" in c["types"] or "locality" in c["types"]), None)
        state = next((c["short_name"] for c in components if "administrative_area_level_1" in c["types"]), None)
        accuracy = result.get("geometry", {}).get("location_type")
        warnings = []
        if result.get("partial_match"):
            warnings.append("correspondência parcial do endereço")
        if accuracy in ("APPROXIMATE", "GEOMETRIC_CENTER"):
            warnings.append("ponto aproximado (centro da área, não o lote)")
        if municipality and city and _norm(city) != _norm(municipality):
            warnings.append(f"município encontrado ({city}) difere do cadastrado ({municipality})")
        if not _in_brazil(lat, lon):
            warnings.append("fora do Brasil")
        rows.append({"formatted_address": result.get("formatted_address"), "latitude": round(lat, 6), "longitude": round(lon, 6),
                     "accuracy": accuracy, "place_id": result.get("place_id"), "municipality": city, "state": state,
                     "types": result.get("types", []), "warnings": warnings})
    return rows


class GeocodeRequest(BaseModel):
    address: str | None = Field(default=None, max_length=300)


class LocationUpdate(BaseModel):
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    source: str | None = None
    accuracy: str | None = Field(default=None, max_length=30)
    place_id: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def check(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be informed together")
        if self.latitude is not None and self.source not in SOURCES:
            raise ValueError("source must be one of " + ", ".join(SOURCES))
        if self.source == "GEOCODED" and not self.place_id:
            raise ValueError("place_id is required for geocoded locations")
        return self


def apply_location(project: Project, subject: str, payload: LocationUpdate) -> None:
    project.latitude, project.longitude = payload.latitude, payload.longitude
    located = payload.latitude is not None
    project.location_source = payload.source if located else None
    project.location_accuracy = payload.accuracy if located else None
    project.location_place_id = payload.place_id if located and payload.source == "GEOCODED" else None
    project.location_confirmed_by = subject if located else None
    project.location_confirmed_at = datetime.now(timezone.utc) if located else None


def location_info(project: Project, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    confirmed = project.location_confirmed_at
    if confirmed is not None and confirmed.tzinfo is None:
        confirmed = confirmed.replace(tzinfo=timezone.utc)
    expired = project.location_source == "GEOCODED" and confirmed is not None and now - confirmed > timedelta(days=CACHE_DAYS)
    return {"latitude": None if project.latitude is None else float(project.latitude),
            "longitude": None if project.longitude is None else float(project.longitude),
            "source": project.location_source, "accuracy": project.location_accuracy, "place_id": project.location_place_id,
            "confirmed_by": project.location_confirmed_by, "confirmed_at": confirmed.isoformat() if confirmed else None,
            "refresh_due": expired}


@router.post("/projects/{project_id}/geocode")
def geocode(project_id: str, payload: GeocodeRequest, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    """Candidates only — nothing is saved until a person confirms one through PUT /location."""
    project = access(db, subject, project_id, EDIT_ROLES)
    address = (payload.address or project.address or "").strip()
    if not address:
        raise HTTPException(status_code=422, detail="Inform the address to geocode")
    parts = [address]
    if project.municipality and _norm(project.municipality) not in _norm(address):
        parts.append(project.municipality)
    query = ", ".join(parts)
    data = _call_geocoding({"address": query, "components": "country:BR"})
    return {"query": query, "candidates": candidates(data, project.municipality)}


@router.put("/projects/{project_id}/location")
def set_location(project_id: str, payload: LocationUpdate, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    project = access(db, subject, project_id, EDIT_ROLES)
    project = db.scalar(select(Project).where(Project.id == project.id).with_for_update())
    if payload.latitude is not None and not _in_brazil(float(payload.latitude), float(payload.longitude)):
        raise HTTPException(status_code=422, detail="Coordinates outside Brazil")
    apply_location(project, subject, payload)
    db.add(AuditEvent(organization_id=project.organization_id, subject_id=subject,
                      action="project.location:" + (payload.source or "cleared"), resource_id=project.id))
    db.commit()
    return {"id": project.id, "location": location_info(project)}


@router.post("/geo/refresh")
def refresh_geocoded(subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    """Refreshes geocoded coordinates older than 30 days by place ID (required by the Google Maps Platform terms)."""
    projects = db.scalars(select(Project).join(Membership, Membership.organization_id == Project.organization_id)
                          .where(Membership.subject_id == subject, Membership.role.in_(EDIT_ROLES),
                                 Project.location_source == "GEOCODED")).all()
    refreshed, removed = [], []
    for project in projects:
        if not location_info(project)["refresh_due"]:
            continue
        found = candidates(_call_geocoding({"place_id": project.location_place_id}), None)
        if found:
            project.latitude, project.longitude = Decimal(str(found[0]["latitude"])), Decimal(str(found[0]["longitude"]))
            project.location_confirmed_at = datetime.now(timezone.utc)
            refreshed.append(project.id)
        else:  # place no longer resolvable: delete the cached coordinates instead of keeping stale Google data
            project.latitude = project.longitude = project.location_source = project.location_accuracy = None
            project.location_place_id = project.location_confirmed_by = project.location_confirmed_at = None
            removed.append(project.id)
        db.add(AuditEvent(organization_id=project.organization_id, subject_id=subject, action="project.location:refresh",
                          resource_id=project.id))
    db.commit()
    return {"refreshed": refreshed, "removed": removed}


def risk(schedule: dict, cost: dict, status: str) -> dict:
    """Simple, explainable risk class for the map marker, from the same forecasts shown in the panel."""
    if status == "DONE":
        return {"level": "concluida", "reasons": []}
    reasons, level = [], "baixo"
    order = {"baixo": 0, "medio": 1, "alto": 2}

    def raise_to(new: str, reason: str):
        nonlocal level
        reasons.append(reason)
        if order[new] > order[level]:
            level = new

    probability = schedule.get("probability_on_time")
    if schedule.get("status") == "ok" and probability is not None and probability < 0.7:
        raise_to("alto" if probability < 0.4 else "medio", f"{round(probability * 100)}% de chance de cumprir o prazo")
    budget, eac = cost.get("budget"), cost.get("eac_p50")
    if cost.get("status") == "ok" and budget and eac and eac > budget:
        overrun = eac / budget - 1
        raise_to("alto" if overrun > 0.05 else "medio", f"custo final estimado {overrun * 100:.0f}% acima do orçamento")
    if schedule.get("status") != "ok" and cost.get("status") != "ok":
        return {"level": "sem_dados", "reasons": ["dados insuficientes para prever prazo e custo"]}
    return {"level": level, "reasons": reasons}


@router.get("/map/projects")
def map_projects(subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    rows = db.execute(select(Project, Organization).join(Organization, Organization.id == Project.organization_id)
                      .join(Membership, Membership.organization_id == Project.organization_id)
                      .where(Membership.subject_id == subject, Membership.role.in_(READ_ROLES), Project.status != "COST_POOL")
                      .order_by(Project.name)).all()
    result = []
    for project, organization in rows:
        intel = project_intelligence(db, project)
        schedule, cost = intel["schedule"], intel["cost"]
        result.append({"id": project.id, "name": project.name, "organization": organization.name, "status": project.status,
                       "municipality": project.municipality, "address": project.address, "responsible": project.responsible,
                       "source": project.source, "progress": schedule.get("current_progress"),
                       "finish_p50": schedule.get("finish_p50"), "probability_on_time": schedule.get("probability_on_time"),
                       "eac_p50": cost.get("eac_p50"), "budget": cost.get("budget"),
                       "risk": risk(schedule, cost, project.status), "location": location_info(project)})
    db.commit()  # forecast runs recorded while computing the risk
    return {"projects": result, "maps_configured": bool(os.getenv("GOOGLE_MAPS_SERVER_KEY"))}


@router.get("/projects/{project_id}/location")
def get_location(project_id: str, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    project = access(db, subject, project_id, READ_ROLES)
    return {"id": project.id, "name": project.name, "address": project.address, "municipality": project.municipality,
            "location": location_info(project), "can_edit": _can_edit(db, subject, project)}


def _can_edit(db: Session, subject: str, project: Project) -> bool:
    role = db.scalar(select(Membership.role).where(Membership.organization_id == project.organization_id, Membership.subject_id == subject))
    return role in EDIT_ROLES
