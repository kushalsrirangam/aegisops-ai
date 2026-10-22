"""Exercise migrations, vector search, workflow decisions, and persistence on PostgreSQL."""

import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.main import app
from app.models.entities import AgentRun, Approval, KnowledgeChunk, Proposal, Report

DATABASE_URL = os.getenv("INTEGRATION_DATABASE_URL")
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DATABASE_URL, reason="INTEGRATION_DATABASE_URL is not set"),
]


@pytest.fixture
def postgres_client():
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.fail("Integration tests require PostgreSQL")

    def override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as client:
            yield client, engine
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


@pytest.mark.parametrize(
    "decision,expected_status", [("approve", "complete"), ("reject", "rejected")]
)
def test_postgres_workflow(postgres_client, decision, expected_status):
    client, engine = postgres_client
    token = uuid4().hex
    source = f"integration/{token}/migration-runbook.md"
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")) == 1
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0001"
        assert connection.scalar(
            text("SELECT format_type(atttypid, atttypmod) FROM pg_attribute "
                 "WHERE attrelid = 'knowledge_chunks'::regclass AND attname = 'embedding'")
        ) == "vector(64)"

    response = client.post(
        "/api/v1/knowledge/documents",
        json={
            "title": "Checkout migration runbook",
            "content": "Checkout database missing column customer_tier after deployment migration. "
                       "Inspect the schema and apply the approved migration before retrying.",
            "source": source,
        },
    )
    assert response.status_code == 201, response.text
    document_id = response.json()["id"]

    response = client.get(
        "/api/v1/knowledge/search",
        params={"q": "checkout database missing column customer_tier migration"},
    )
    assert response.status_code == 200, response.text
    assert any(hit["source"] == source and hit["score"] > 0 for hit in response.json())

    response = client.post(
        "/api/v1/incidents",
        json={
            "title": "Checkout missing column customer_tier",
            "description": "Checkout requests fail after deployment migration",
            "service": f"checkout-{token[:8]}",
            "evidence": {
                "logs": ["DatabaseError: column customer_tier does not exist"],
                "error_rate": 0.37,
            },
        },
    )
    assert response.status_code == 201, response.text
    incident_id = response.json()["id"]
    response = client.post(f"/api/v1/incidents/{incident_id}/analyze")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "awaiting_approval"
    run_id = response.json()["run_id"]
    proposal_id = response.json()["proposal_id"]
    assert proposal_id is not None

    response = client.get(f"/api/v1/agents/runs/{run_id}")
    assert response.status_code == 200
    assert len(response.json()["steps"]) == 6
    assert client.get(f"/api/v1/incidents/{incident_id}/report").status_code == 404

    response = client.post(
        f"/api/v1/approvals/{proposal_id}/{decision}",
        json={"actor": "integration-test", "reason": "Verified decision path"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == expected_status
    assert response.json()["decision"] == (
        "approved" if decision == "approve" else "rejected"
    )
    assert any(item["source"] == source for item in response.json()["sources"])
    assert client.get(f"/api/v1/incidents/{incident_id}/report").json() == response.json()
    assert client.post(
        f"/api/v1/approvals/{proposal_id}/{decision}", json={"actor": "integration-test"}
    ).status_code == 409

    # A new session proves the API committed every record to PostgreSQL.
    with Session(engine) as session:
        assert session.get(KnowledgeChunk, session.scalar(
            select(KnowledgeChunk.id).where(KnowledgeChunk.document_id == document_id)
        )) is not None
        run = session.get(AgentRun, run_id)
        proposal = session.get(Proposal, proposal_id)
        assert run.status == expected_status
        assert len(run.steps) == 7
        assert proposal.status == ("approved" if decision == "approve" else "rejected")
        approval = session.scalar(select(Approval).where(Approval.proposal_id == proposal_id))
        assert approval.decision == proposal.status
        report = session.scalar(select(Report).where(Report.incident_id == incident_id))
        assert report.content["status"] == expected_status
