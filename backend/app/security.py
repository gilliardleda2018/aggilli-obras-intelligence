"""Fail-closed boundary: replace with verified OIDC JWT and database memberships before exposing writes."""
from fastapi import HTTPException, status

def require_identity():
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Authenticated identity provider not configured")
