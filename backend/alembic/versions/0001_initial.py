"""Initial relational schema."""
from alembic import op
import sqlalchemy as sa
from app.core.db import Base
from app.models import entities  # noqa: F401

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    # These two tables are created at their original shape so later revisions
    # can add columns even when this revision runs against the latest models.
    entities.Incident.__table__.create(bind=op.get_bind(), checkfirst=True)
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("incident_id", sa.Integer(), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_runs_incident_id", "agent_runs", ["incident_id"])
    # Keep the original revision stable as later models are added.
    tables = [
        table
        for table in Base.metadata.sorted_tables
        if table.name not in {"users", "auth_sessions", "login_throttles"}
    ]
    Base.metadata.create_all(bind=op.get_bind(), tables=tables)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
