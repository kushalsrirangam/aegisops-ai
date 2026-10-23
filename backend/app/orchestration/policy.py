"""Deny-by-default policy for proposals shown to a human reviewer.

This module authorizes review only. It never authorizes infrastructure execution.
"""

MIGRATION_REVIEW = "review_migration_or_rollback"
MIGRATION_ACTION = (
    "Run the reviewed database migration, then redeploy or roll back v2.4.1 "
    "through the normal release pipeline"
)
PROPOSAL_CATALOG = {MIGRATION_REVIEW: {"action": MIGRATION_ACTION, "risk": "medium"}}


def evaluate_proposal(state: dict) -> dict:
    """Return an auditable decision for the exact proposed review operation."""
    operation = state.get("operation")
    specification = PROPOSAL_CATALOG.get(operation) if isinstance(operation, str) else None
    service = state.get("service")
    target = state.get("target_service")

    if specification is None:
        reason = "operation_not_allowed"
    elif not isinstance(service, str) or not service or target != service:
        reason = "target_service_mismatch"
    elif state.get("execution_mode") != "proposal_only":
        reason = "execution_not_allowed"
    elif state.get("risk") != specification["risk"]:
        reason = "risk_mismatch"
    elif state.get("action") != specification["action"]:
        reason = "action_mismatch"
    else:
        reason = "allowed_for_review"

    return {
        "blocked": reason != "allowed_for_review",
        "reason": reason,
        "operation": operation,
        "target_service": target,
        "approval_required": True,
        "execution_allowed": False,
        "policy_version": "1",
    }
