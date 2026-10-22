"""Initial relational schema."""
from alembic import op
from app.core.db import Base
from app.models import entities  # noqa: F401

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    # Keep the original revision stable as later models are added.
    tables = [
        table
        for table in Base.metadata.sorted_tables
        if table.name not in {"users", "auth_sessions"}
    ]
    Base.metadata.create_all(bind=op.get_bind(), tables=tables)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
