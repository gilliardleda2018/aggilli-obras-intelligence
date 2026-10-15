"""30-day system license issued by the Aggilli license control (Aggilli Agro server).

Ported from the MG Transportes system (same server, same rules). The installation behaves like an Aggilli collector: it has its own Ed25519 device key,
activates with the code e-mailed after payment (POST /api/v1/licencas/ativar) and keeps
the signed license. Renewals made in the control panel extend the same license on the
server; the next refresh (re-activation with the same code and device) brings the new
expiry. Nothing here can extend a license locally:

* the signature is checked against the *pinned* Aggilli public key (not the one the
  server returns), and
* the license must belong to the Agro record reserved for this obras installation
  (``OBRAS_LICENSE_FARM_UID``), so another system's code cannot unlock it.
"""
import base64
import json
import os
import secrets
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from .db import Base
from .models import AuditEvent

DEFAULT_SERVER = "https://agro.aggillintelligence.com.br"
# Public key of the Aggilli license server (GET /api/v1/licencas/chave-publica, 2026-10-14).
DEFAULT_PUBLIC_KEY = "qyrQCdwM_yBMkyUH8-6nZt1Rn5Xp4EGDotHumIsUOuA"
WARN_DAYS = 7
GRACE_DAYS = 5
BRT = timezone(timedelta(hours=-3))
REFRESH_ACTIVE = timedelta(hours=6)
REFRESH_URGENT = timedelta(minutes=10)


class SystemLicense(Base):
    """Single row (id=1) for the whole installation; holds the device key and the signed license."""
    __tablename__ = "system_license"
    __table_args__ = (CheckConstraint("id = 1", name="ck_system_license_single_row"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    device_id: Mapped[str] = mapped_column(String(64), nullable=False)
    device_key: Mapped[str] = mapped_column(String(64), nullable=False)  # raw Ed25519 private key, base64url
    device_mac: Mapped[str] = mapped_column(String(17), nullable=False)
    activation_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    token: Mapped[str | None] = mapped_column(Text, nullable=True)
    license_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(300), nullable=True)


class LicenseError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    server: str
    public_key: str
    farm_id: int
    enforce: bool
    farm_uid: str = ""   # unique record ID shown in the Agro (preferred over farm_id)

    @property
    def record_set(self) -> bool:
        return bool(self.farm_uid or self.farm_id)

    def matches(self, claims: dict) -> bool:
        if self.farm_uid:
            return str(claims.get("farm_uid", "")).lower() == self.farm_uid
        return bool(self.farm_id) and claims.get("farm_id") == self.farm_id


def config(env=None) -> Config:
    env = os.environ if env is None else env
    try:
        farm_id = int(env.get("OBRAS_LICENSE_FARM_ID") or 0)
    except ValueError:
        farm_id = 0
    return Config(server=(env.get("OBRAS_LICENSE_SERVER") or DEFAULT_SERVER).rstrip("/"),
                  public_key=env.get("OBRAS_LICENSE_PUBLIC_KEY") or DEFAULT_PUBLIC_KEY, farm_id=farm_id,
                  farm_uid=(env.get("OBRAS_LICENSE_FARM_UID") or "").strip().lower(),
                  enforce=str(env.get("OBRAS_LICENSE_ENFORCE", "")).lower() in ("1", "true", "yes", "sim"))


@dataclass(frozen=True)
class Status:
    state: str            # missing | active | expiring | grace | blocked
    expires_at: datetime | None
    days_left: int | None
    farm_name: str | None
    email: str | None
    last_error: str | None
    checked_at: datetime | None

    @property
    def blocked(self) -> bool:
        return self.state in ("missing", "blocked")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _aware(value: datetime | None) -> datetime | None:
    return value.replace(tzinfo=timezone.utc) if value is not None and value.tzinfo is None else value


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _private(row: SystemLicense) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(_unb64(row.device_key))


def _public_b64(row: SystemLicense) -> str:
    return _b64(_private(row).public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw))


def device(db: Session) -> SystemLicense:
    """The installation identity, created once (concurrent first runs converge on id=1)."""
    row = db.get(SystemLicense, 1)
    if row is not None:
        return row
    key = Ed25519PrivateKey.generate().private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
                                                     serialization.NoEncryption())
    # Locally administered unicast MAC: stable identity required by the activation API.
    mac = ":".join(["02"] + [f"{b:02x}" for b in secrets.token_bytes(5)])
    try:
        with db.begin_nested():
            db.add(SystemLicense(id=1, device_id=f"aggilli-obras-{uuid.uuid4().hex}", device_key=_b64(key),
                                 device_mac=mac))
    except IntegrityError:
        pass
    return db.get(SystemLicense, 1)


def verify(token: str, row: SystemLicense, cfg: Config, *, check_record: bool = True) -> dict:
    """Signature, issuer, device and reserved record; expiry is evaluated separately (grace period)."""
    try:
        payload, signature = token.split(".")
        Ed25519PublicKey.from_public_bytes(_unb64(cfg.public_key)).verify(_unb64(signature), payload.encode())
        claims = json.loads(_unb64(payload))
    except Exception as exc:
        raise LicenseError("Licença com assinatura inválida.") from exc
    if claims.get("iss") != "Aggilli-Coletor" or claims.get("version") != 1:
        raise LicenseError("Emissor da licença inválido.")
    if claims.get("device_id") != row.device_id or claims.get("public_key") != _public_b64(row):
        raise LicenseError("Licença emitida para outra instalação.")
    if check_record and not cfg.matches(claims):
        raise LicenseError("Este código não é uma licença do Aggilli Obras.")
    if not isinstance(claims.get("exp"), int):
        raise LicenseError("Licença sem validade.")
    return claims


def _post(url: str, body: dict, timeout: float) -> dict:
    request = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed https server
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 422):
            raise LicenseError("Ativação recusada pelo servidor Aggilli: código inválido, vencido, revogado "
                               "ou já usado em outra instalação.") from exc
        raise LicenseError(f"Servidor de licenças indisponível (HTTP {exc.code}).") from exc
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise LicenseError("Não foi possível falar com o servidor de licenças Aggilli.") from exc


def _activate_remote(row: SystemLicense, code: str, cfg: Config, post, timeout: float,
                     check_record: bool = True) -> dict:
    result = post(f"{cfg.server}/api/v1/licencas/ativar",
                  {"activation_code": code, "device_id": row.device_id, "public_key": _public_b64(row),
                   "mac": row.device_mac}, timeout)
    token = result.get("license") if isinstance(result, dict) else None
    if not isinstance(token, str):
        raise LicenseError("Resposta do servidor de licenças sem licença assinada.")
    claims = verify(token, row, cfg, check_record=check_record)
    return {"token": token, "claims": claims}


def _store(row: SystemLicense, code: str, signed: dict) -> None:
    row.activation_code = code
    row.token = signed["token"]
    row.license_id = str(signed["claims"].get("license_id", ""))[:36] or None
    row.expires_at = datetime.fromtimestamp(signed["claims"]["exp"], timezone.utc)
    row.checked_at = _now()
    row.last_error = None


def activate(db: Session, code: str, *, organization_id: str, actor: str, cfg: Config | None = None,
             post=None) -> Status:
    """Administrator pastes the code received by e-mail; the installation is bound to it."""
    cfg, post = cfg or config(), post or _post
    code = (code or "").strip()
    for line in code.splitlines():  # accept the whole e-mail block ("Código: xxx")
        if ":" in line and len(line.split(":", 1)[1].strip()) >= 20:
            code = line.split(":", 1)[1].strip()
    if not 20 <= len(code) <= 120 or any(ch.isspace() for ch in code):
        raise LicenseError("Cole o código de ativação recebido por e-mail.")
    row = device(db)
    if not cfg.record_set:
        # First setup: the property ID is not shown in the Aggilli panels, so reveal it from the signed
        # license (genuine signature, bound to this installation) without accepting the license yet.
        claims = _activate_remote(row, code, cfg, post, timeout=15, check_record=False)["claims"]
        db.flush()
        raise LicenseError(f"Código válido da propriedade “{claims.get('farm_name') or '—'}” "
                           f"(ID {claims.get('farm_id')}, identificador {claims.get('farm_uid') or '—'}). Informe este ID à Aggilli para concluir a configuração; "
                           "depois, clique em Ativar licença com o mesmo código.")
    signed = _activate_remote(row, code, cfg, post, timeout=15)
    _store(row, code, signed)
    db.add(AuditEvent(organization_id=organization_id, subject_id=actor, action="system_license.activate",
                      resource_id=str(row.license_id or "1")[:36]))
    db.flush()
    return status(db, cfg)


def refresh(db: Session, cfg: Config | None = None, post=None, *, force: bool = False, timeout: float = 5) -> None:
    """Re-activate with the stored code to pick up renewals. Failures keep the current license."""
    cfg, post = cfg or config(), post or _post
    row = db.get(SystemLicense, 1)
    if row is None or not row.activation_code or not cfg.record_set:
        return
    now = _now()
    expires, checked = _aware(row.expires_at), _aware(row.checked_at)
    urgent = expires is None or expires - now <= timedelta(days=WARN_DAYS)
    if not force and checked and now - checked < (REFRESH_URGENT if urgent else REFRESH_ACTIVE):
        return
    row.checked_at = now
    try:
        signed = _activate_remote(row, row.activation_code, cfg, post, timeout)
    except LicenseError as exc:
        row.last_error = str(exc)[:300]
        return
    if datetime.fromtimestamp(signed["claims"]["exp"], timezone.utc) >= (expires or now):
        _store(row, row.activation_code, signed)


def status(db: Session, cfg: Config | None = None, now: datetime | None = None) -> Status:
    cfg = cfg or config()
    now = now or _now()
    row = db.get(SystemLicense, 1)
    claims, expires = {}, None
    if row is not None and row.token:
        try:
            claims = verify(row.token, row, cfg)
            expires = datetime.fromtimestamp(claims["exp"], timezone.utc)
        except LicenseError:
            claims = {}
    common = dict(farm_name=claims.get("farm_name"), email=claims.get("email"),
                  last_error=row.last_error if row else None, checked_at=_aware(row.checked_at) if row else None)
    if expires is None:
        return Status("missing", None, None, **common)
    left = expires - now
    days = int(left.total_seconds() // 86400)
    if left > timedelta(days=WARN_DAYS):
        state = "active"
    elif left > timedelta(0):
        state = "expiring"
    elif left > -timedelta(days=GRACE_DAYS):
        state = "grace"
    else:
        state = "blocked"
    return Status(state, expires, days, **common)


def grace_ends(st: Status) -> datetime | None:
    return st.expires_at + timedelta(days=GRACE_DAYS) if st.expires_at else None


def ensure_fresh(db: Session, cfg: Config | None = None) -> Status:
    """Called once per page run: throttled refresh, then the current status."""
    cfg = cfg or config()
    try:
        refresh(db, cfg)
        db.commit()
    except Exception:  # never let the license check break the app
        db.rollback()
    return status(db, cfg)
