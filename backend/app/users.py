"""Users and access, as in MG Transportes: e-mail + password login, administrators manage the company's users.

A new user gets a temporary password shown once to the administrator and must change it at the first login.
Five wrong passwords lock the account for 15 minutes. Passwords are stored only as PBKDF2-SHA256 hashes.
"""
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import license
from .db import get_db
from .models import AuditEvent, Membership, Organization, User
from .security import issue_token, require_identity

router = APIRouter(prefix="/api/v1", tags=["users"])
ROLES = ("OWNER", "ADMIN", "ENGINEER", "INSPECTOR", "FIELD_OPERATOR", "VIEWER")
MANAGERS = ("OWNER", "ADMIN")
ITERATIONS = 600_000
MAX_ATTEMPTS, LOCK_MINUTES = 5, 15
SESSION_HOURS, REMEMBER_HOURS = 12, 24 * 30
TEMP_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITERATIONS).hex()
    return f"pbkdf2_sha256${ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt, digest = stored.split("$")
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations)).hex()
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(candidate, digest)


def check_strength(password: str) -> None:
    if len(password) < 10 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise HTTPException(status_code=422, detail="A senha precisa ter pelo menos 10 caracteres, com letras e números")


def temporary_password() -> str:
    while True:
        value = "".join(secrets.choice(TEMP_ALPHABET) for _ in range(12))
        if re.search(r"[A-Za-z]", value) and re.search(r"\d", value):
            return value


def _aware(moment: datetime | None) -> datetime | None:
    return moment.replace(tzinfo=timezone.utc) if moment is not None and moment.tzinfo is None else moment


def _norm(email: str) -> str:
    return email.strip().lower()


def create_user(db: Session, email: str, name: str, password: str, must_change: bool = True) -> User:
    user = User(email=_norm(email), name=name.strip(), password_hash=hash_password(password), must_change_password=must_change,
                password_changed_at=datetime.now(timezone.utc))
    db.add(user)
    db.flush()
    return user


# ---------- Login and own account ----------

class Login(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=200)
    remember: bool = False


@router.post("/auth/login")
def login(payload: Login, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == _norm(payload.email)))
    now = datetime.now(timezone.utc)
    if user and _aware(user.locked_until) and _aware(user.locked_until) > now:
        raise HTTPException(status_code=423, detail="Conta bloqueada por tentativas erradas. Tente de novo em alguns minutos.")
    if not user or not user.active or not verify_password(payload.password, user.password_hash):
        if user:
            user.failed_attempts += 1
            if user.failed_attempts >= MAX_ATTEMPTS:
                user.failed_attempts, user.locked_until = 0, now + timedelta(minutes=LOCK_MINUTES)
            db.commit()
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")
    user.failed_attempts, user.locked_until, user.last_login_at = 0, None, now
    db.commit()
    hours = REMEMBER_HOURS if payload.remember else SESSION_HOURS
    return {"access_token": issue_token(user, hours), "token_type": "bearer", "expires_in": hours * 3600,
            "must_change_password": user.must_change_password}


def _memberships(db: Session, subject: str):
    return db.execute(select(Membership, Organization).join(Organization, Organization.id == Membership.organization_id)
                      .where(Membership.subject_id == subject).order_by(Organization.name)).all()


@router.get("/me")
def me(subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    user = db.get(User, subject)
    orgs = [{"id": org.id, "name": org.name, "role": m.role} for m, org in _memberships(db, subject)]
    st = license.status(db)
    return {"id": subject, "email": user.email if user else None, "name": user.name if user else subject,
            "must_change_password": bool(user and user.must_change_password), "local": user is not None,
            "organizations": orgs,
            "license": {"enforced": license.config().enforce, "state": st.state, "days_left": st.days_left,
                        "expires_at": st.expires_at.isoformat() if st.expires_at else None,
                        "grace_ends": license.grace_ends(st).isoformat() if st.expires_at else None}}


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=1, max_length=200)


@router.post("/me/password")
def change_password(payload: PasswordChange, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    user = db.get(User, subject)
    if not user:
        raise HTTPException(status_code=409, detail="Esta conta entra pelo provedor externo; a senha é trocada lá")
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=403, detail="Senha atual incorreta")
    check_strength(payload.new_password)
    if verify_password(payload.new_password, user.password_hash):
        raise HTTPException(status_code=422, detail="A nova senha precisa ser diferente da atual")
    user.password_hash, user.must_change_password = hash_password(payload.new_password), False
    user.password_changed_at = datetime.now(timezone.utc) + timedelta(seconds=1)  # ends every other session
    for m, _ in _memberships(db, subject):
        db.add(AuditEvent(organization_id=m.organization_id, subject_id=subject, action="user.password_change", resource_id=user.id))
    db.commit()
    hours = SESSION_HOURS
    return {"access_token": issue_token(user, hours), "token_type": "bearer", "expires_in": hours * 3600}


# ---------- Administration (OWNER / ADMIN of the organization) ----------

def _manager_role(db: Session, subject: str, organization_id: str) -> str:
    role = db.scalar(select(Membership.role).where(Membership.organization_id == organization_id, Membership.subject_id == subject))
    if role not in MANAGERS:
        raise HTTPException(status_code=404, detail="Organização não encontrada")
    return role


def _member_json(m: Membership, user: User | None) -> dict:
    return {"membership_id": m.id, "user_id": m.subject_id, "role": m.role,
            "email": user.email if user else None, "name": user.name if user else m.subject_id,
            "active": user.active if user else True, "must_change_password": bool(user and user.must_change_password),
            "locked": bool(user and _aware(user.locked_until) and _aware(user.locked_until) > datetime.now(timezone.utc)),
            "last_login_at": _aware(user.last_login_at).isoformat() if user and user.last_login_at else None,
            "local": user is not None}


@router.get("/organizations/{organization_id}/users")
def list_users(organization_id: str, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    _manager_role(db, subject, organization_id)
    rows = db.execute(select(Membership, User).outerjoin(User, User.id == Membership.subject_id)
                      .where(Membership.organization_id == organization_id)).all()
    return sorted((_member_json(m, u) for m, u in rows), key=lambda r: (r["name"] or "").lower())


class NewUser(BaseModel):
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    name: str = Field(min_length=2, max_length=120)
    role: str = Field(pattern="^(" + "|".join(ROLES) + ")$")


def _guard_owner(actor_role: str, role: str) -> None:
    if role == "OWNER" and actor_role != "OWNER":
        raise HTTPException(status_code=403, detail="Só um dono pode dar o perfil de dono")


@router.post("/organizations/{organization_id}/users", status_code=201)
def add_user(organization_id: str, payload: NewUser, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    actor_role = _manager_role(db, subject, organization_id)
    _guard_owner(actor_role, payload.role)
    user = db.scalar(select(User).where(User.email == _norm(payload.email)))
    password = None
    if user is None:
        password = temporary_password()
        user = create_user(db, payload.email, payload.name, password)
    elif db.scalar(select(Membership.id).where(Membership.organization_id == organization_id, Membership.subject_id == user.id)):
        raise HTTPException(status_code=409, detail="Este e-mail já tem acesso a esta empresa")
    membership = Membership(organization_id=organization_id, subject_id=user.id, role=payload.role)
    db.add(membership)
    db.add(AuditEvent(organization_id=organization_id, subject_id=subject, action="user.add", resource_id=user.id))
    db.commit()
    # The temporary password is shown once, to the administrator, and never stored in clear.
    return {**_member_json(membership, user), "temporary_password": password}


class UserChange(BaseModel):
    role: str | None = Field(default=None, pattern="^(" + "|".join(ROLES) + ")$")
    active: bool | None = None


def _target(db: Session, organization_id: str, user_id: str) -> tuple[Membership, User | None]:
    membership = db.scalar(select(Membership).where(Membership.organization_id == organization_id, Membership.subject_id == user_id))
    if not membership:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return membership, db.get(User, user_id)


def _keep_a_manager(db: Session, organization_id: str, leaving: Membership) -> None:
    others = db.scalar(select(func.count()).select_from(Membership).outerjoin(User, User.id == Membership.subject_id).where(
        Membership.organization_id == organization_id, Membership.id != leaving.id, Membership.role.in_(MANAGERS),
        (User.id.is_(None)) | (User.active.is_(True))))
    if not others:
        raise HTTPException(status_code=409, detail="A empresa precisa de pelo menos um administrador ativo")


@router.patch("/organizations/{organization_id}/users/{user_id}")
def change_user(organization_id: str, user_id: str, payload: UserChange, subject: str = Depends(require_identity),
                db: Session = Depends(get_db)):
    actor_role = _manager_role(db, subject, organization_id)
    membership, user = _target(db, organization_id, user_id)
    if membership.role == "OWNER" and actor_role != "OWNER":
        raise HTTPException(status_code=403, detail="Só um dono altera outro dono")
    if payload.role and payload.role != membership.role:
        _guard_owner(actor_role, payload.role)
        if membership.role in MANAGERS and payload.role not in MANAGERS:
            _keep_a_manager(db, organization_id, membership)
        membership.role = payload.role
    if payload.active is not None and user and payload.active != user.active:
        if not payload.active:
            if user.id == subject:
                raise HTTPException(status_code=409, detail="Você não pode desativar o próprio acesso")
            if membership.role in MANAGERS:
                _keep_a_manager(db, organization_id, membership)
        user.active = payload.active
    db.add(AuditEvent(organization_id=organization_id, subject_id=subject, action="user.change", resource_id=user_id))
    db.commit()
    return _member_json(membership, user)


@router.post("/organizations/{organization_id}/users/{user_id}/reset-password")
def reset_password(organization_id: str, user_id: str, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    actor_role = _manager_role(db, subject, organization_id)
    membership, user = _target(db, organization_id, user_id)
    if not user:
        raise HTTPException(status_code=409, detail="Este usuário entra pelo provedor externo")
    if membership.role == "OWNER" and actor_role != "OWNER":
        raise HTTPException(status_code=403, detail="Só um dono redefine a senha de outro dono")
    password = temporary_password()
    user.password_hash, user.must_change_password = hash_password(password), True
    user.failed_attempts, user.locked_until = 0, None
    user.password_changed_at = datetime.now(timezone.utc) + timedelta(seconds=1)  # ends the user's open sessions
    db.add(AuditEvent(organization_id=organization_id, subject_id=subject, action="user.reset_password", resource_id=user_id))
    db.commit()
    return {**_member_json(membership, user), "temporary_password": password}


# ---------- System license (OWNER / ADMIN of any organization) ----------

class Activation(BaseModel):
    code: str = Field(min_length=20, max_length=4000)


@router.get("/license")
def license_status(subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    cfg = license.config()
    st = license.ensure_fresh(db, cfg)
    return {"enforced": cfg.enforce, "configured": cfg.record_set, "state": st.state, "days_left": st.days_left,
            "expires_at": st.expires_at.isoformat() if st.expires_at else None,
            "grace_ends": license.grace_ends(st).isoformat() if st.expires_at else None,
            "holder": st.farm_name, "email": st.email, "last_error": st.last_error,
            "can_manage": any(m.role in MANAGERS for m, _ in _memberships(db, subject))}


@router.post("/license/activate")
def activate_license(payload: Activation, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    managed = [m for m, _ in _memberships(db, subject) if m.role in MANAGERS]
    if not managed:
        raise HTTPException(status_code=403, detail="Somente administradores ativam a licença")
    try:
        license.activate(db, payload.code, organization_id=managed[0].organization_id, actor=subject)
    except license.LicenseError as error:
        db.commit()  # keeps the installation key created for the activation attempt
        raise HTTPException(status_code=422, detail=str(error))
    db.commit()
    return license_status(subject, db)
