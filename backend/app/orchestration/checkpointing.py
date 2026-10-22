"""Compile a workflow with a durable PostgreSQL or test-only memory checkpointer."""

import os
from contextlib import contextmanager

os.environ.setdefault("LANGGRAPH_STRICT_MSGPACK", "true")

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres import PostgresSaver

from app.core.config import get_settings
from app.orchestration.graph import build_graph

_test_saver = InMemorySaver()


def _postgres_dsn(url) -> str:
    return url.set(drivername="postgresql").render_as_string(hide_password=False)


@contextmanager
def workflow_graph(db):
    if db.bind.dialect.name == "postgresql":
        with PostgresSaver.from_conn_string(_postgres_dsn(db.bind.url)) as saver:
            yield build_graph(checkpointer=saver, interactive=True)
    else:
        yield build_graph(checkpointer=_test_saver, interactive=True)


def setup() -> None:
    """Initialize LangGraph's tables after Alembic migrations, before API startup."""
    from sqlalchemy import create_engine

    engine = create_engine(get_settings().database_url)
    try:
        if engine.dialect.name == "postgresql":
            with PostgresSaver.from_conn_string(_postgres_dsn(engine.url)) as saver:
                saver.setup()
    finally:
        engine.dispose()


if __name__ == "__main__":
    setup()
