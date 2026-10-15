import os
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import jwt
from jwt import PyJWKClient, PyJWKSet
from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from .db import get_db

# Local login (e-mail + password, as in MG Transportes): HS256 tokens signed with LOCAL_AUTH_SECRET.
LOCAL_ISSUER = "aggilli-obras"
LOCAL_AUDIENCE = "aggilli-obras-api"
# Reachable while the system license is suspended, so an administrator can still sign in and renew it.
LICENSE_FREE_PREFIXES = ("/api/v1/auth/", "/api/v1/me", "/api/v1/license")


@lru_cache(maxsize=8)
def jwks_client(url: str):
    return PyJWKClient(url, cache_jwk_set=True, lifespan=300)

def _dev_jwks_key(path: str, token: str):
    """Development identity only (scripts/dev_identity.py): JWKS read from a local file."""
    kid = jwt.get_unverified_header(token).get("kid")
    with open(path, encoding="utf-8") as handle:
        keys = PyJWKSet.from_json(handle.read()).keys
    return next(k.key for k in keys if k.key_id == kid)


def local_secret() -> str | None:
    secret = os.getenv("LOCAL_AUTH_SECRET", "")
    return secret if len(secret) >= 32 else None


def _epoch(moment: datetime) -> int:
    return int((moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)).timestamp())


def issue_token(user, hours: int) -> str:
    secret = local_secret()
    if not secret:
        raise HTTPException(status_code=503, detail="Login local não configurado")
    issued = datetime.now(timezone.utc)
    return jwt.encode({"iss": LOCAL_ISSUER, "aud": LOCAL_AUDIENCE, "sub": user.id, "iat": issued,
                       "exp": issued + timedelta(hours=hours), "pwv": _epoch(user.password_changed_at)}, secret, algorithm="HS256")


def _local_subject(token: str, db: Session) -> str:
    from .models import User
    claims = jwt.decode(token, local_secret(), algorithms=["HS256"], issuer=LOCAL_ISSUER, audience=LOCAL_AUDIENCE,
                        options={"require": ["exp", "iat", "sub", "iss", "aud"]}, leeway=30)
    user = db.get(User, str(claims["sub"]))
    # A deactivated user, or a password changed/reset after the token was issued, ends the session at once.
    if not user or not user.active or int(claims.get("pwv", 0)) < _epoch(user.password_changed_at):
        raise jwt.InvalidTokenError("revoked")
    return user.id


def _oidc_subject(token: str) -> str:
    issuer = os.getenv("OIDC_ISSUER", "").rstrip("/")
    audience = os.getenv("OIDC_AUDIENCE", "")
    jwks_url = os.getenv("OIDC_JWKS_URL", "")
    # Never honoured in production: there the identity provider must publish JWKS over HTTPS.
    jwks_file = "" if os.getenv("APP_ENV", "").lower() == "production" else os.getenv("OIDC_JWKS_FILE", "")
    if not issuer or not audience or not (jwks_url.startswith("https://") or jwks_file):
        raise HTTPException(status_code=503, detail="Identity provider not configured")
    key = _dev_jwks_key(jwks_file, token) if jwks_file else jwks_client(jwks_url).get_signing_key_from_jwt(token).key
    claims = jwt.decode(token, key, algorithms=["RS256"], issuer=issuer,
                        audience=audience, options={"require":["exp","iat","sub","iss","aud"]},
                        leeway=30)
    return str(claims["sub"])


def _check_license(request: Request, db: Session) -> None:
    from . import license
    cfg = license.config()
    if not cfg.enforce or request.url.path.startswith(LICENSE_FREE_PREFIXES):
        return
    if license.ensure_fresh(db, cfg).blocked:
        raise HTTPException(status_code=402, detail="Licença do sistema vencida ou não ativada")


def _oidc_configured() -> bool:
    jwks_file = "" if os.getenv("APP_ENV", "").lower() == "production" else os.getenv("OIDC_JWKS_FILE", "")
    return bool(os.getenv("OIDC_ISSUER") and os.getenv("OIDC_AUDIENCE")
                and (os.getenv("OIDC_JWKS_URL", "").startswith("https://") or jwks_file))


def require_identity(request: Request, authorization: str | None = Header(default=None),
                     db: Session = Depends(get_db)) -> str:
    if not local_secret() and not _oidc_configured():
        raise HTTPException(status_code=503, detail="Identity provider not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")
    token = authorization[7:]
    try:
        local = jwt.get_unverified_header(token).get("alg") == "HS256" and local_secret()
        subject = _local_subject(token, db) if local else _oidc_subject(token)
    except (jwt.PyJWTError, ValueError, TypeError, StopIteration, OSError):
        raise HTTPException(status_code=401, detail="Invalid token") from None
    _check_license(request, db)
    return subject
