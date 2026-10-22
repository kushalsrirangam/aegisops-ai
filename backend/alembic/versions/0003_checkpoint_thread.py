"""Link agent runs to durable LangGraph checkpoint threads."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_runs", sa.Column("checkpoint_thread_id", sa.String(64), nullable=True))
    op.create_unique_constraint(
        "uq_agent_runs_checkpoint_thread_id", "agent_runs", ["checkpoint_thread_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_agent_runs_checkpoint_thread_id", "agent_runs", type_="unique")
    op.drop_column("agent_runs", "checkpoint_thread_id")
