"""Local users (e-mail + password, as in MG Transportes) and the 30-day system license.

Revision ID: 0014_users_license
Revises: 0013_field_documents
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_users_license"
down_revision = "0013_field_documents"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("password_hash", sa.String(200), nullable=False),
        sa.Column("active", sa.Boolean, nullable=False),
        sa.Column("must_change_password", sa.Boolean, nullable=False),
        sa.Column("failed_attempts", sa.Integer, nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "system_license",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=False),
        sa.Column("device_id", sa.String(64), nullable=False),
        sa.Column("device_key", sa.String(64), nullable=False),
        sa.Column("device_mac", sa.String(17), nullable=False),
        sa.Column("activation_code", sa.String(120), nullable=True),
        sa.Column("token", sa.Text, nullable=True),
        sa.Column("license_id", sa.String(36), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(300), nullable=True),
        sa.CheckConstraint("id = 1", name="ck_system_license_single_row"),
    )


def downgrade():
    op.drop_table("system_license")
    op.drop_table("users")
