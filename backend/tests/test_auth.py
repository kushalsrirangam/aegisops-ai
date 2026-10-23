from datetime import timedelta

from sqlalchemy import select

from app.core.auth import create_user, issue_session, session_for_token
from app.core.login_throttle import (
    ACCOUNT_FAILURE_LIMIT,
    IP_FAILURE_LIMIT,
    authenticate,
    reset_password,
    unlock_user,
)
from app.models.entities import Approval, utcnow


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
    assert client.post(
        "/api/v1/incidents",
        json={
            "title": "Another incident",
            "description": "Reviewer cannot create an incident",
            "service": "checkout-api",
        },
    ).status_code == 403
    response = client.post(
        f"/api/v1/approvals/{proposal_id}/approve", json={"actor": "spoofed"}
    )
    assert response.status_code == 200
    approval = db.scalar(select(Approval).where(Approval.proposal_id == proposal_id))
    assert approval.actor == "reviewer@example.test"


def test_account_lockout_is_independent_of_client_ip(client, db):
    client.headers.pop("Authorization")
    for attempt in range(ACCOUNT_FAILURE_LIMIT):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.test", "password": "wrong-password"},
        )
        assert response.status_code == (429 if attempt == ACCOUNT_FAILURE_LIMIT - 1 else 401)
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.test", "password": "strong-test-password"},
    ).status_code == 429
    # The account limit follows the user even if the caller changes IP address.
    user, throttled = authenticate(db, "admin@example.test", "strong-test-password", "another-ip")
    assert user is None and throttled


def test_account_lock_expires_and_success_resets_failures(db):
    create_user(db, "rate@example.test", "strong-test-password", "operator")
    start = utcnow()
    for _ in range(ACCOUNT_FAILURE_LIMIT):
        user, throttled = authenticate(db, "rate@example.test", "wrong", "client-a", now=start)
    assert user is None and throttled
    user, throttled = authenticate(
        db, "rate@example.test", "strong-test-password", "client-b", now=start + timedelta(minutes=16)
    )
    assert user is not None and not throttled
    for _ in range(ACCOUNT_FAILURE_LIMIT - 1):
        user, throttled = authenticate(
            db, "rate@example.test", "wrong", "client-c", now=start + timedelta(minutes=17)
        )
        assert user is None and not throttled


def test_ip_limit_catches_password_spraying(db):
    for attempt in range(IP_FAILURE_LIMIT):
        user, throttled = authenticate(
            db, f"unknown-{attempt}@example.test", "wrong", "same-ip"
        )
        assert user is None
        assert throttled is (attempt == IP_FAILURE_LIMIT - 1)
    create_user(db, "real@example.test", "strong-test-password", "operator")
    user, throttled = authenticate(db, "real@example.test", "strong-test-password", "same-ip")
    assert user is None and throttled
    user, throttled = authenticate(db, "real@example.test", "strong-test-password", "other-ip")
    assert user is not None and not throttled


def test_unlock_and_password_reset_revoke_sessions(db):
    user = create_user(db, "recover@example.test", "strong-test-password", "operator")
    token, _ = issue_session(db, user)
    for _ in range(ACCOUNT_FAILURE_LIMIT):
        authenticate(db, user.email, "wrong", "client-a")
    unlock_user(db, user.email)
    logged_in, throttled = authenticate(db, user.email, "strong-test-password", "client-b")
    assert logged_in is not None and not throttled
    reset_password(db, user.email, "replacement-password")
    assert session_for_token(db, token) is None
    old, _ = authenticate(db, user.email, "strong-test-password", "client-c")
    new, throttled = authenticate(db, user.email, "replacement-password", "client-c")
    assert old is None and new is not None and not throttled


def test_unknown_account_uses_generic_errors(client):
    client.headers.pop("Authorization")
    for attempt in range(ACCOUNT_FAILURE_LIMIT):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "missing@example.test", "password": "wrong-password"},
        )
        assert response.status_code == (429 if attempt == ACCOUNT_FAILURE_LIMIT - 1 else 401)
        assert response.json()["detail"] == (
            "Too many login attempts. Try again later"
            if attempt == ACCOUNT_FAILURE_LIMIT - 1
            else "Invalid credentials"
        )
