from app.core.auth import create_user, issue_session
from app.models.entities import Approval
from sqlalchemy import select


def test_login_logout_and_protected_reads(client, db):
    client.headers.pop("Authorization")
    assert client.get("/api/v1/incidents").status_code == 401
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.test", "password": "wrong-password"},
    ).status_code == 401
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.test", "password": "strong-test-password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    assert response.json()["user"]["role"] == "admin"
    client.headers.update({"Authorization": f"Bearer {token}"})
    assert client.get("/api/v1/auth/me").json()["email"] == "admin@example.test"
    assert client.get("/api/v1/incidents").status_code == 200
    assert client.post("/api/v1/auth/logout").status_code == 200
    assert client.get("/api/v1/incidents").status_code == 401


def test_roles_and_reviewer_identity(client, db):
    operator = create_user(db, "operator@example.test", "strong-test-password", "operator")
    reviewer = create_user(db, "reviewer@example.test", "strong-test-password", "reviewer")
    operator_token, _ = issue_session(db, operator)
    reviewer_token, _ = issue_session(db, reviewer)
    client.headers.update({"Authorization": f"Bearer {operator_token}"})
    response = client.post(
        "/api/v1/incidents",
        json={
            "title": "Checkout HTTP 500",
            "description": "Missing database column after deployment",
            "service": "checkout-api",
        },
    )
    assert response.status_code == 201
    incident_id = response.json()["id"]
    proposal_id = client.post(f"/api/v1/incidents/{incident_id}/analyze").json()["proposal_id"]
    assert client.post(
        f"/api/v1/approvals/{proposal_id}/approve", json={"actor": "spoofed"}
    ).status_code == 403

    client.headers.update({"Authorization": f"Bearer {reviewer_token}"})
    assert client.post("/api/v1/incidents", json={}).status_code == 403
    response = client.post(
        f"/api/v1/approvals/{proposal_id}/approve", json={"actor": "spoofed"}
    )
    assert response.status_code == 200
    approval = db.scalar(select(Approval).where(Approval.proposal_id == proposal_id))
    assert approval.actor == "reviewer@example.test"
