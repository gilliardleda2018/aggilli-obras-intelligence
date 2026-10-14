import os
from functools import lru_cache
import jwt
from jwt import PyJWKClient
from fastapi import Header, HTTPException

@lru_cache(maxsize=8)
def jwks_client(url: str):
    return PyJWKClient(url, cache_jwk_set=True, lifespan=300)

def require_identity(authorization: str | None = Header(default=None)) -> str:
    issuer = os.getenv("OIDC_ISSUER", "").rstrip("/")
    audience = os.getenv("OIDC_AUDIENCE", "")
    jwks_url = os.getenv("OIDC_JWKS_URL", "")
    if not issuer or not audience or not jwks_url:
        raise HTTPException(status_code=503, detail="Identity provider not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")
    try:
        key = jwks_client(jwks_url).get_signing_key_from_jwt(authorization[7:]).key
        claims = jwt.decode(authorization[7:], key, algorithms=["RS256"], issuer=issuer,
                            audience=audience, options={"require":["exp","iat","sub","iss","aud"]},
                            leeway=30)
        return str(claims["sub"])
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token") from None
