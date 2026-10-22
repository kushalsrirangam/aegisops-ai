from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.orchestration.graph import GRAPH, build_graph, security, validation
from app.rag.retrieval import ingest, retrieve

SAMPLE = {
    "title": "Checkout returns HTTP 500",
    "description": "Failure after deployment",
    "service": "checkout-api",
    "logs": ["DatabaseError: column customer_tier does not exist"],
    "error_rate": 0.37,
    "knowledge": [],
    "steps": [],
}


def test_graph_routes_to_approval_then_validation():
    state = GRAPH.invoke(SAMPLE, {"recursion_limit": 16})
    assert state["phase"] == "awaiting_approval"
    assert [s["agent"] for s in state["steps"]] == [
        "triage",
        "investigation",
        "knowledge",
        "supervisor",
        "remediation",
        "security",
    ]
    assert "missing" in state["hypothesis"].lower() or "column" in state["hypothesis"].lower()
    final = GRAPH.invoke({**state, "decision": "approved"}, {"recursion_limit": 16})
    assert final["phase"] == "complete"
    assert final["steps"][-1]["agent"] == "validation"
    rejected = GRAPH.invoke({**state, "decision": "rejected"}, {"recursion_limit": 16})
    assert rejected["phase"] == "rejected"


def test_interactive_graph_pauses_and_resumes_from_checkpoint():
    graph = build_graph(InMemorySaver(), interactive=True)
    config = {"configurable": {"thread_id": "workflow-test"}, "recursion_limit": 16}
    pending = graph.invoke({**SAMPLE, "incident_id": 1}, config)
    assert pending["phase"] == "awaiting_approval"
    assert pending["__interrupt__"]
    assert graph.get_state(config).next == ("approval",)
    result = graph.invoke(Command(resume="approved"), config)
    assert result["phase"] == "complete"
    assert len(result["steps"]) == 7
    assert graph.get_state(config).next == ()


def test_low_confidence_escalates():
    result = GRAPH.invoke({**SAMPLE, "logs": ["HTTP 500"]}, {"recursion_limit": 16})
    assert result["phase"] == "escalated"


def test_security_blocks_destructive_proposal():
    result = security({"steps": [], "action": "drop table customers"})
    assert result["blocked"] is True


def test_bedrock_approval_stays_unverified():
    result = validation({"steps": [], "mode": "bedrock", "decision": "approved"})
    assert result["phase"] == "needs_verification"
    assert result["steps"][-1]["result"]["simulated"] is False


def test_retrieval_has_attributable_source(db):
    ingest(
        db,
        "Migration runbook",
        "missing database column after deployment migration",
        "runbooks/migrations.md",
    )
    hits = retrieve(db, "missing column migration")
    assert hits and hits[0]["source"] == "runbooks/migrations.md"


def test_incident_api_and_decisions(client):
    created = client.post(
        "/api/v1/incidents",
        json={
            "title": "Checkout returns 500",
            "description": "Requests fail after deployment with missing column",
            "service": "checkout-api",
        },
    )
    assert created.status_code == 201
    incident_id = created.json()["id"]
    assert client.get(f"/api/v1/incidents/{incident_id}/report").status_code == 404
    analyzed = client.post(f"/api/v1/incidents/{incident_id}/analyze")
    assert analyzed.status_code == 200
    assert analyzed.json()["status"] == "awaiting_approval"
    proposal_id = analyzed.json()["proposal_id"]
    assert client.post(f"/api/v1/incidents/{incident_id}/analyze").status_code == 409
    approved = client.post(f"/api/v1/approvals/{proposal_id}/approve", json={"actor": "tester"})
    assert approved.status_code == 200
    assert approved.json()["status"] == "complete"
    assert approved.json()["mode"] == "demo"
    assert (
        client.post(
            f"/api/v1/approvals/{proposal_id}/approve", json={"actor": "tester"}
        ).status_code
        == 409
    )
    run = client.get(f"/api/v1/agents/runs/{analyzed.json()['run_id']}").json()
    assert len(run["steps"]) == 7
    assert client.get(f"/api/v1/incidents/{incident_id}/report").json()["decision"] == "approved"


def test_rejection_and_validation_errors(client):
    invalid = client.post(
        "/api/v1/incidents", json={"title": "x", "description": "bad", "service": "!"}
    )
    assert invalid.status_code == 422
    assert client.get("/api/v1/incidents/9999").status_code == 404
    created = client.post(
        "/api/v1/incidents",
        json={
            "title": "Payments returns 500",
            "description": "New release causes server errors",
            "service": "payments",
        },
    ).json()
    proposal_id = client.post(f"/api/v1/incidents/{created['id']}/analyze").json()["proposal_id"]
    rejected = client.post(
        f"/api/v1/approvals/{proposal_id}/reject", json={"actor": "operator", "reason": "defer"}
    )
    assert rejected.json()["status"] == "rejected"
