"""Work diary (diário de obra) with geotagged photos.

The original file is stored untouched and identified by its SHA-256, so a photo can later be shown to be the one that was
sent. Location has an explicit provenance: EXIF (GPS written by the camera when the picture was taken) or DEVICE (phone
position when the photo was sent). Nothing is estimated: a photo without either is shown as "sem localização".
Whether a photo was taken on site is computed against the project's confirmed location, with the GPS accuracy as margin.
"""
import hashlib
import io
import math
import warnings
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import ExifTags, Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import storage
from .db import get_db
from .geo import BRAZIL
from .measurements import access
from .models import AuditEvent, FieldPhoto, FieldReport, Project, ServiceItem
from .security import require_identity

router = APIRouter(prefix="/api/v1", tags=["diary"])
READ_ROLES = ["OWNER", "ADMIN", "ENGINEER", "INSPECTOR", "FIELD_OPERATOR", "VIEWER"]
WRITE_ROLES = ["OWNER", "ADMIN", "ENGINEER", "INSPECTOR", "FIELD_OPERATOR"]
MAX_BYTES = 15 * 1024 * 1024
MAX_PIXELS = 60_000_000
FORMATS = {"JPEG": ("image/jpeg", "jpg"), "PNG": ("image/png", "png"), "WEBP": ("image/webp", "webp")}
SITE_RADIUS_M = 300          # a work site plus the street in front of it
MAX_ACCURACY_MARGIN_M = 500  # a phone reporting worse accuracy than this does not make a far photo "on site"
LOCAL_TZ = timezone(timedelta(hours=-3))  # Maranhão; used only when EXIF has no offset


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _in_brazil(lat: float, lon: float) -> bool:
    return BRAZIL[0] <= lat <= BRAZIL[1] and BRAZIL[2] <= lon <= BRAZIL[3]


def _dms(values, ref) -> float | None:
    try:
        d, m, s = (float(v) for v in values)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    value = d + m / 60 + s / 3600
    return -value if str(ref).upper() in ("S", "W") else value


def read_exif(image: Image.Image) -> dict:
    """GPS position and capture time written by the camera, when present and plausible."""
    out: dict = {}
    try:
        exif = image.getexif()
    except Exception:  # corrupt metadata must not reject the photo itself
        return out
    gps = exif.get_ifd(ExifTags.IFD.GPSInfo) if exif else {}
    if gps and 2 in gps and 4 in gps:
        lat, lon = _dms(gps.get(2), gps.get(1)), _dms(gps.get(4), gps.get(3))
        if lat is not None and lon is not None and (lat, lon) != (0, 0) and _in_brazil(lat, lon):
            out["latitude"], out["longitude"] = round(lat, 6), round(lon, 6)
    detail = exif.get_ifd(ExifTags.IFD.Exif) if exif else {}
    raw, offset = detail.get(36867), detail.get(36881)  # DateTimeOriginal, OffsetTimeOriginal
    if raw:
        try:
            taken = datetime.strptime(str(raw).strip(), "%Y:%m:%d %H:%M:%S")
            tz = LOCAL_TZ
            if offset and len(str(offset)) >= 6:
                sign = -1 if str(offset)[0] == "-" else 1
                tz = timezone(sign * timedelta(hours=int(str(offset)[1:3]), minutes=int(str(offset)[4:6])))
            out["taken_at"] = taken.replace(tzinfo=tz)
        except ValueError:
            pass
    return out


def place_status(photo: FieldPhoto, project: Project) -> tuple[str, int | None]:
    """NA_OBRA | FORA_DA_OBRA | SEM_LOCALIZACAO | OBRA_SEM_LOCAL, plus the distance to the site in metres."""
    if photo.latitude is None or photo.longitude is None:
        return "SEM_LOCALIZACAO", None
    if project.latitude is None or project.longitude is None:
        return "OBRA_SEM_LOCAL", None
    meters = round(distance_m(float(photo.latitude), float(photo.longitude), float(project.latitude), float(project.longitude)))
    margin = min(float(photo.accuracy_m or 0), MAX_ACCURACY_MARGIN_M)
    return ("NA_OBRA" if meters <= SITE_RADIUS_M + margin else "FORA_DA_OBRA"), meters


def photo_json(photo: FieldPhoto, project: Project, services: dict[str, str]) -> dict:
    status, meters = place_status(photo, project)
    return {"id": photo.id, "report_id": photo.report_id, "service_id": photo.service_id, "service": services.get(photo.service_id or ""),
            "caption": photo.caption, "url": "/photos/" + photo.id + "/file", "width": photo.width, "height": photo.height,
            "size_bytes": photo.size_bytes, "sha256": photo.sha256,
            "taken_at": _local(photo.taken_at).isoformat() if photo.taken_at else None, "taken_at_source": photo.taken_at_source,
            "latitude": float(photo.latitude) if photo.latitude is not None else None,
            "longitude": float(photo.longitude) if photo.longitude is not None else None,
            "accuracy_m": float(photo.accuracy_m) if photo.accuracy_m is not None else None,
            "location_source": photo.location_source, "place": status, "distance_m": meters,
            "recorded_by": photo.recorded_by, "created_at": _local(photo.created_at).isoformat()}


def _local(moment: datetime) -> datetime:
    """Stored in UTC; SQLite returns it without offset."""
    return (moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)).astimezone(LOCAL_TZ)


def _local_day(moment: datetime) -> date:
    return _local(moment).date()


async def read_image(file: UploadFile) -> tuple[bytes, Image.Image]:
    """The uploaded bytes and the decoded picture; rejects anything that is not a sane JPEG/PNG/WEBP."""
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Foto maior que 15 MB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(io.BytesIO(data))
            if image.format not in FORMATS or image.width * image.height > MAX_PIXELS:
                raise HTTPException(status_code=415, detail="Envie uma foto JPEG, PNG ou WEBP")
            image.verify()
        return data, Image.open(io.BytesIO(data))  # verify() leaves the object unusable
    except (UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning, OSError, SyntaxError):
        raise HTTPException(status_code=415, detail="Arquivo não é uma foto válida")


@router.post("/projects/{project_id}/photos", status_code=201)
async def upload_photo(project_id: str, file: UploadFile = File(...), report_id: str | None = Form(None),
                       service_id: str | None = Form(None), caption: str | None = Form(None),
                       latitude: float | None = Form(None), longitude: float | None = Form(None),
                       accuracy: float | None = Form(None), taken_at: datetime | None = Form(None),
                       subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    project = access(db, subject, project_id, WRITE_ROLES)
    if report_id and not db.scalar(select(FieldReport.id).where(FieldReport.id == report_id, FieldReport.project_id == project.id)):
        raise HTTPException(status_code=422, detail="Relato não pertence a esta obra")
    if service_id and not db.scalar(select(ServiceItem.id).where(ServiceItem.id == service_id, ServiceItem.project_id == project.id)):
        raise HTTPException(status_code=422, detail="Etapa não pertence a esta obra")
    if (latitude is None) != (longitude is None):
        raise HTTPException(status_code=422, detail="Latitude e longitude devem vir juntas")
    if latitude is not None and not _in_brazil(latitude, longitude):
        raise HTTPException(status_code=422, detail="Posição do aparelho fora do Brasil")
    if accuracy is not None and not 0 <= accuracy <= 100_000:
        raise HTTPException(status_code=422, detail="Precisão inválida")
    if caption is not None and len(caption) > 300:
        raise HTTPException(status_code=422, detail="Legenda muito longa (máximo 300 caracteres)")

    data, image = await read_image(file)
    exif = read_exif(image)
    digest = hashlib.sha256(data).hexdigest()
    content_type, ext = FORMATS[image.format]
    photo = FieldPhoto(project_id=project.id, report_id=report_id or None, service_id=service_id or None,
                       caption=(caption or "").strip() or None, storage_key="", content_type=content_type, size_bytes=len(data),
                       sha256=digest, width=image.width, height=image.height, recorded_by=subject)
    if "latitude" in exif:  # the camera's own position at capture time beats where the phone is when sending
        photo.latitude, photo.longitude, photo.location_source = Decimal(str(exif["latitude"])), Decimal(str(exif["longitude"])), "EXIF"
    elif latitude is not None:
        photo.latitude, photo.longitude, photo.location_source = Decimal(f"{latitude:.6f}"), Decimal(f"{longitude:.6f}"), "DEVICE"
        photo.accuracy_m = Decimal(f"{accuracy:.1f}") if accuracy is not None else None
    if "taken_at" in exif:
        photo.taken_at, photo.taken_at_source = exif["taken_at"].astimezone(timezone.utc), "EXIF"
    elif taken_at is not None:
        photo.taken_at, photo.taken_at_source = (taken_at if taken_at.tzinfo else taken_at.replace(tzinfo=LOCAL_TZ)).astimezone(timezone.utc), "DEVICE"
    db.add(photo)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Esta foto já foi enviada para esta obra")
    photo.storage_key = photo.id + "." + ext
    status, meters = place_status(photo, project)
    photo.distance_m = meters
    storage.save(photo.storage_key, data, content_type)
    db.add(AuditEvent(organization_id=project.organization_id, subject_id=subject, action="field_photo.create", resource_id=photo.id))
    try:
        db.commit()
    except Exception:
        storage.delete(photo.storage_key)
        raise
    services = dict(db.execute(select(ServiceItem.id, ServiceItem.name).where(ServiceItem.project_id == project.id)).all())
    return photo_json(photo, project, services)


@router.get("/projects/{project_id}/photos")
def list_photos(project_id: str, service_id: str | None = None, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    project = access(db, subject, project_id, READ_ROLES)
    query = select(FieldPhoto).where(FieldPhoto.project_id == project.id)
    if service_id:
        query = query.where(FieldPhoto.service_id == service_id)
    services = dict(db.execute(select(ServiceItem.id, ServiceItem.name).where(ServiceItem.project_id == project.id)).all())
    rows = db.scalars(query.order_by(FieldPhoto.created_at.desc())).all()
    return [photo_json(photo, project, services) for photo in rows]


@router.get("/photos/{photo_id}/file")
def photo_file(photo_id: str, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    photo = db.get(FieldPhoto, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Foto não encontrada")
    access(db, subject, photo.project_id, READ_ROLES)
    data = storage.load(photo.storage_key)
    if data is None:
        raise HTTPException(status_code=404, detail="Arquivo da foto indisponível")
    return Response(data, media_type=photo.content_type, headers={"Cache-Control": "private, max-age=86400"})


@router.get("/projects/{project_id}/diary")
def diary(project_id: str, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    """Day by day: what was reported and the photos of that day (by report, else by capture time, else by upload time)."""
    project = access(db, subject, project_id, READ_ROLES)
    services = dict(db.execute(select(ServiceItem.id, ServiceItem.name).where(ServiceItem.project_id == project.id)
                               .order_by(ServiceItem.name)).all())
    reports = db.scalars(select(FieldReport).where(FieldReport.project_id == project.id)).all()
    photos = db.scalars(select(FieldPhoto).where(FieldPhoto.project_id == project.id).order_by(FieldPhoto.created_at)).all()
    report_day = {report.id: report.report_date for report in reports}
    days: dict[date, dict] = {}
    for report in reports:
        days.setdefault(report.report_date, {"reports": [], "photos": []})["reports"].append(
            {"id": report.id, "weather": report.weather, "summary": report.summary, "recorded_by": report.recorded_by})
    for photo in photos:
        day = report_day.get(photo.report_id or "") or _local_day(photo.taken_at or photo.created_at)
        days.setdefault(day, {"reports": [], "photos": []})["photos"].append(photo_json(photo, project, services))
    return {"project": {"id": project.id, "name": project.name, "located": project.latitude is not None},
            "services": [{"id": key, "name": name} for key, name in services.items()],
            "days": [{"date": day.isoformat(), **days[day]} for day in sorted(days, reverse=True)]}
