import os
from functools import lru_cache
import jwt
from jwt import PyJWKClient, PyJWKSet
from fastapi import Header, HTTPException

@lru_cache(maxsize=8)
def jwks_client(url: str):
    return PyJWKClient(url, cache_jwk_set=True, lifespan=300)

def _dev_jwks_key(path: str, token: str):
    """Development identity only (scripts/dev_identity.py): JWKS read from a local file."""
    kid = jwt.get_unverified_header(token).get("kid")
    with open(path, encoding="utf-8") as handle:
        keys = PyJWKSet.from_json(handle.read()).keys
    return next(k.key for k in keys if k.key_id == kid)

def require_identity(authorization: str | None = Header(default=None)) -> str:
    issuer = os.getenv("OIDC_ISSUER", "").rstrip("/")
    audience = os.getenv("OIDC_AUDIENCE", "")
    jwks_url = os.getenv("OIDC_JWKS_URL", "")
    # Never honoured in production: there the identity provider must publish JWKS over HTTPS.
    jwks_file = "" if os.getenv("APP_ENV", "").lower() == "production" else os.getenv("OIDC_JWKS_FILE", "")
    if not issuer or not audience or not (jwks_url.startswith("https://") or jwks_file):
        raise HTTPException(status_code=503, detail="Identity provider not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")
    token = authorization[7:]
    try:
        key = _dev_jwks_key(jwks_file, token) if jwks_file else jwks_client(jwks_url).get_signing_key_from_jwt(token).key
        claims = jwt.decode(token, key, algorithms=["RS256"], issuer=issuer,
                            audience=audience, options={"require":["exp","iat","sub","iss","aud"]},
                            leeway=30)
        return str(claims["sub"])
    except (jwt.PyJWTError, ValueError, TypeError, StopIteration, OSError):
        raise HTTPException(status_code=401, detail="Invalid token") from None
