"""Local development identity: an RSA key and JWKS on disk, and tokens signed with it.

Never for production — the API ignores OIDC_JWKS_FILE when APP_ENV=production, and this script refuses to
run in that environment. Files live in backend/.dev/ (git-ignored).

    python -m scripts.dev_identity init                   # create key + jwks, print the env vars to use
    python -m scripts.dev_identity token --sub dev-owner  # print an access token (8 h)
"""
import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

DEV = Path(__file__).resolve().parents[1] / ".dev"
KEY = DEV / "dev-signing-key.pem"
JWKS = DEV / "jwks.json"
ISSUER = "https://dev-obras.localhost"
AUDIENCE = "aggilli-obras-api"
KID = "dev-1"


def init() -> None:
    DEV.mkdir(exist_ok=True)
    if not KEY.exists():
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        KEY.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                          serialization.NoEncryption()))
    key = serialization.load_pem_private_key(KEY.read_bytes(), password=None)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    JWKS.write_text(json.dumps({"keys": [{**jwk, "kid": KID, "use": "sig", "alg": "RS256"}]}), encoding="utf-8")
    print(f"OIDC_ISSUER={ISSUER}")
    print(f"OIDC_AUDIENCE={AUDIENCE}")
    print(f"OIDC_JWKS_FILE={JWKS.resolve().as_posix()}")


def token(subject: str, hours: float) -> str:
    key = serialization.load_pem_private_key(KEY.read_bytes(), password=None)
    now = int(time.time())
    claims = {"iss": ISSUER, "aud": AUDIENCE, "sub": subject, "iat": now, "exp": now + int(hours * 3600),
              "jti": str(uuid.uuid4())}
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": KID})


def main(argv=None) -> int:
    if os.getenv("APP_ENV", "").lower() == "production":
        sys.exit("dev_identity is not available in production")
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    t = sub.add_parser("token")
    t.add_argument("--sub", required=True)
    t.add_argument("--hours", type=float, default=8)
    args = parser.parse_args(argv)
    if args.cmd == "init":
        init()
    else:
        if not KEY.exists():
            sys.exit("Run 'init' first")
        print(token(args.sub, args.hours))
    return 0


if __name__ == "__main__":
    sys.exit(main())
