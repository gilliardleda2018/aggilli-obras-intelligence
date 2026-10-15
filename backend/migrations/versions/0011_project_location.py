"""Project location provenance: how the coordinates were obtained, who confirmed them and the Google place ID.

Revision ID: 0011_project_location
Revises: 0010_materials_stock
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_project_location"
down_revision = "0010_materials_stock"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("location_source", sa.String(20), nullable=True))
        batch.add_column(sa.Column("location_accuracy", sa.String(30), nullable=True))
        batch.add_column(sa.Column("location_place_id", sa.String(300), nullable=True))
        batch.add_column(sa.Column("location_confirmed_by", sa.String(200), nullable=True))
        batch.add_column(sa.Column("location_confirmed_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_check_constraint("ck_projects_location_source", "location_source IN ('GEOCODED','MAP','FIELD','MANUAL')")


def downgrade():
    with op.batch_alter_table("projects") as batch:
        batch.drop_constraint("ck_projects_location_source", type_="check")
        for column in ("location_confirmed_at", "location_confirmed_by", "location_place_id", "location_accuracy", "location_source"):
            batch.drop_column(column)
