"""First administrator of an installation (run once, e.g. as a one-off ECS task with the API image).

    python -m scripts.bootstrap_admin --email dono@empresa.com.br --name "Nome" --organization "Grupo MG"

Creates the organization if needed and an OWNER user with a temporary password (changed at the first login).
With BOOTSTRAP_SECRET_ARN set, the password is written to that AWS Secrets Manager secret instead of the output,
so it never lands in the logs; the owner reads it once in the AWS console.
"""
import argparse
import json
import os

from sqlalchemy import select

from app.db import SessionLocal
from app.models import AuditEvent, Membership, Organization, User
from app.users import create_user, temporary_password


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--organization", required=True)
    args = parser.parse_args()
    with SessionLocal() as db:
        org = db.scalar(select(Organization).where(Organization.name == args.organization))
        if org is None:
            org = Organization(name=args.organization)
            db.add(org)
            db.flush()
        if db.scalar(select(User.id).where(User.email == args.email.strip().lower())):
            raise SystemExit("Já existe um usuário com este e-mail; use a tela Usuários para dar acesso.")
        password = temporary_password()
        user = create_user(db, args.email, args.name, password)
        db.add(Membership(organization_id=org.id, subject_id=user.id, role="OWNER"))
        db.add(AuditEvent(organization_id=org.id, subject_id="bootstrap", action="user.bootstrap_owner", resource_id=user.id))
        db.commit()
    secret = os.getenv("BOOTSTRAP_SECRET_ARN")
    if secret:
        import boto3
        boto3.client("secretsmanager").put_secret_value(SecretId=secret, SecretString=json.dumps(
            {"email": args.email.strip().lower(), "temporary_password": password, "organization": args.organization}))
        print(f"Dono criado em {args.organization}: {args.email}. Senha temporária gravada no Secrets Manager.")
    else:
        print(f"Dono criado em {args.organization}: {args.email}\nSenha temporária: {password}")


if __name__ == "__main__":
    main()
