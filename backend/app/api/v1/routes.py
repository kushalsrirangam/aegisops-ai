from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import current_user, require_role
from app.core.db import get_db
from app.models.entities import (
    AgentRun,
    AgentStep,
    IncidentEvent,
    KnowledgeDocument,
    Proposal,
    Report,
    User,
)
from app.rag.retrieval import ingest, retrieve
from app.schemas.api import DecisionIn, DocumentIn, IncidentCreate, IncidentOut
from app.services import incidents as service

router = APIRouter(prefix="/api/v1", dependencies=[Depends(current_user)])


@router.get("/incidents", response_model=list[IncidentOut])
def incidents(
    db: Session = Depends(get_db),
    status: str | None = None,
    severity: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    return service.list_incidents(db, status, severity, offset, limit)


@router.post("/incidents", response_model=IncidentOut, status_code=201)
def create_incident(
    payload: IncidentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("operator")),
):
    return service.create_incident(db, **payload.model_dump())


@router.get("/incidents/{incident_id}", response_model=IncidentOut)
def incident(incident_id: int, db: Session = Depends(get_db)):
    return service.get_incident(db, incident_id)


@router.post("/incidents/{incident_id}/analyze")
def analyze(
    incident_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("operator")),
):
    run = service.analyze(db, incident_id)
    proposal = db.scalar(select(Proposal).where(Proposal.run_id == run.id))
    return {
        "run_id": run.id,
        "status": run.status,
        "proposal_id": proposal.id if proposal else None,
    }


@router.get("/incidents/{incident_id}/timeline")
def timeline(incident_id: int, db: Session = Depends(get_db)):
    service.get_incident(db, incident_id)
    return [
        {"kind": e.kind, "message": e.message, "created_at": e.created_at}
        for e in db.scalars(
            select(IncidentEvent)
            .where(IncidentEvent.incident_id == incident_id)
            .order_by(IncidentEvent.id)
        )
    ]


@router.get("/incidents/{incident_id}/report")
def report(incident_id: int, db: Session = Depends(get_db)):
    service.get_incident(db, incident_id)
    item = db.scalar(select(Report).where(Report.incident_id == incident_id))
    if not item:
        raise HTTPException(404, "Report not ready")
    return item.content


@router.get("/incidents/{incident_id}/proposal")
def proposal(incident_id: int, db: Session = Depends(get_db)):
    service.get_incident(db, incident_id)
    item = db.scalar(
        select(Proposal).where(Proposal.incident_id == incident_id).order_by(Proposal.id.desc())
    )
    if not item:
        raise HTTPException(404, "Proposal not found")
    return {
        "id": item.id,
        "action": item.action,
        "rationale": item.rationale,
        "risk": item.risk,
        "status": item.status,
    }


@router.get("/agents")
def agents():
    return [
        {"name": name, "responsibility": description}
        for name, description in (
            ("supervisor", "Routes evidence and bounds the workflow"),
            ("triage", "Classifies impact and service"),
            ("investigation", "Correlates logs and root-cause hypotheses"),
            ("knowledge", "Retrieves cited runbooks"),
            ("remediation", "Proposes recovery steps"),
            ("security", "Checks risky operations and approval gates"),
            ("validation", "Reports simulated outcome after decision"),
        )
    ]


@router.get("/agents/runs")
def runs(db: Session = Depends(get_db), limit: int = Query(50, ge=1, le=100)):
    return [
        {"id": r.id, "incident_id": r.incident_id, "status": r.status, "started_at": r.started_at}
        for r in db.scalars(select(AgentRun).order_by(AgentRun.id.desc()).limit(limit))
    ]


@router.get("/agents/runs/{run_id}")
def run(run_id: int, db: Session = Depends(get_db)):
    item = db.get(AgentRun, run_id)
    if not item:
        raise HTTPException(404, "Run not found")
    steps = db.scalars(select(AgentStep).where(AgentStep.run_id == run_id).order_by(AgentStep.id))
    return {
        "id": item.id,
        "incident_id": item.incident_id,
        "status": item.status,
        "steps": [
            {"agent": s.agent, "result": s.result, "created_at": s.created_at} for s in steps
        ],
    }


@router.post("/approvals/{proposal_id}/approve")
def approve(
    proposal_id: int,
    payload: DecisionIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("reviewer")),
):
    return service.decide(db, proposal_id, "approved", user.email, payload.reason).content


@router.post("/approvals/{proposal_id}/reject")
def reject(
    proposal_id: int,
    payload: DecisionIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("reviewer")),
):
    return service.decide(db, proposal_id, "rejected", user.email, payload.reason).content


@router.get("/knowledge/documents")
def documents(db: Session = Depends(get_db)):
    return [
        {"id": d.id, "title": d.title, "source": d.source, "created_at": d.created_at}
        for d in db.scalars(select(KnowledgeDocument).order_by(KnowledgeDocument.id))
    ]


@router.post("/knowledge/documents", status_code=201)
def document(
    payload: DocumentIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("operator")),
):
    try:
        doc = ingest(db, **payload.model_dump())
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Source already exists") from exc
    return {"id": doc.id, "title": doc.title, "source": doc.source}


@router.get("/knowledge/search")
def search(q: str = Query(min_length=2, max_length=500), db: Session = Depends(get_db)):
    return retrieve(db, q)


@router.get("/metrics/summary")
def metrics(db: Session = Depends(get_db)):
    return service.summary(db)
