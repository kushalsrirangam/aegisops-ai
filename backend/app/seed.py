from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.models.entities import Incident, KnowledgeDocument
from app.rag.retrieval import ingest
from app.services.incidents import create_incident


def seed() -> None:
    if get_settings().app_mode != "demo":
        return
    with SessionLocal() as db:
        if not db.scalar(select(KnowledgeDocument.id).limit(1)):
            ingest(
                db,
                "HTTP 500 after deployment runbook",
                "If HTTP 500 errors start after a deployment, compare deployment time with logs. "
                "For a missing database column, check migration status. Review and run the migration "
                "through the release pipeline or roll back the deployment. Require human approval. "
                "Validate recovery with error rate and health checks.",
                "runbooks/http-500-after-deploy.md",
            )
        if not db.scalar(select(Incident.id).limit(1)):
            create_incident(
                db,
                "Checkout API returns HTTP 500 after deployment",
                "After release v2.4.1, checkout requests fail with HTTP 500. "
                "Logs show a missing customer_tier column; migration is pending.",
                "checkout-api",
                {
                    "logs": [
                        "10:02 deploy v2.4.1 completed",
                        "10:04 DatabaseError: column customer_tier does not exist",
                        "10:05 migration 2026_10_22_add_customer_tier pending",
                    ],
                    "error_rate": 0.37,
                },
            )


if __name__ == "__main__":
    seed()
