import math
from uuid import uuid4

from fastapi import HTTPException
from langgraph.types import Command
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.integrations.aws.provider import CloudWatchProvider, MockCloudProvider
from app.models.entities import (
    AgentRun,
    AgentStep,
    Approval,
    AuditLog,
    Incident,
    IncidentEvent,
    Proposal,
    Report,
    utcnow,
)
from app.orchestration.checkpointing import workflow_graph
from app.orchestration.graph import GRAPH
from app.rag.retrieval import retrieve


def get_incident(db: Session, incident_id: int) -> Incident:
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    return incident


def list_incidents(
    db: Session, status: str | None, severity: str | None, offset: int, limit: int
) -> list[Incident]:
    query = select(Incident).order_by(Incident.created_at.desc())
    if status:
        query = query.where(Incident.status == status)
    if severity:
        query = query.where(Incident.severity == severity)
    return list(db.scalars(query.offset(offset).limit(limit)))


def create_incident(
    db: Session, title: str, description: str, service: str, evidence: dict | None = None
) -> Incident:
    incident = Incident(
        title=title,
        description=description,
        service=service,
        evidence=evidence or {},
        mode=get_settings().app_mode,
    )
    db.add(incident)
    db.flush()
    db.add(IncidentEvent(incident_id=incident.id, kind="created", message="Incident created"))
    db.add(AuditLog(incident_id=incident.id, action="incident.created", detail={"mode": "demo"}))
    db.commit()
    db.refresh(incident)
    return incident


def analyze(db: Session, incident_id: int) -> AgentRun:
    incident = get_incident(db, incident_id)
    if incident.status != "open":
        raise HTTPException(409, "Only open incidents can be analyzed")
    settings = get_settings()
    cloud = (
        MockCloudProvider()
        if incident.mode == "demo"
        else CloudWatchProvider(
            settings.aws_region,
            metric_namespace=settings.aws_error_rate_metric_namespace,
            metric_name=settings.aws_error_rate_metric_name,
            metric_dimension_name=settings.aws_error_rate_metric_dimension_name,
        )
    )
    try:
        logs = (
            incident.evidence["logs"]
            if "logs" in incident.evidence
            else cloud.logs(incident.service)
        )
        if "error_rate" in incident.evidence:
            rate = incident.evidence["error_rate"]
            metric_source = "incident evidence"
        elif incident.mode == "demo":
            rate = cloud.error_rate(incident.service)
            metric_source = "simulated"
        elif settings.aws_error_rate_metric_namespace:
            rate = cloud.error_rate(incident.service)
            metric_source = "CloudWatch"
        else:
            rate = None
            metric_source = "unavailable"
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    if not isinstance(logs, list) or any(not isinstance(line, str) for line in logs):
        raise HTTPException(422, "Evidence logs must be a list of strings")
    if rate is not None and (
        isinstance(rate, bool)
        or not isinstance(rate, (int, float))
        or not math.isfinite(rate)
        or not 0 <= rate <= 1
    ):
        raise HTTPException(422, "Evidence error_rate must be a number between 0 and 1")
    state = {
        "incident_id": incident.id,
        "title": incident.title,
        "description": incident.description,
        "service": incident.service,
        "evidence": incident.evidence,
        "logs": logs,
        "error_rate": rate,
        "metric_source": metric_source,
        "knowledge": retrieve(db, incident.title + " " + incident.description),
        "mode": incident.mode,
        "steps": [],
    }
    thread_id = str(uuid4())
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 16}
    try:
        with workflow_graph(db) as graph:
            result = graph.invoke(state, config)
    except Exception as exc:
        db.add(
            AuditLog(
                incident_id=incident.id,
                action="analysis.failed",
                detail={"error_type": type(exc).__name__},
            )
        )
        db.commit()
        raise HTTPException(500, "Investigation failed") from exc
    result.pop("__interrupt__", None)
    run = AgentRun(
        incident_id=incident.id,
        status=result["phase"],
        checkpoint_thread_id=thread_id,
        state=result,
    )
    db.add(run)
    db.flush()
    for step in result["steps"]:
        db.add(AgentStep(run_id=run.id, **step))
    incident.severity = result["severity"]
    incident.status = result["phase"]
    if result["phase"] == "awaiting_approval":
        db.add(
            Proposal(
                incident_id=incident.id,
                run_id=run.id,
                action=result["action"],
                rationale=result["rationale"],
                risk=result["risk"],
            )
        )
    else:
        db.add(Report(incident_id=incident.id, content=_report(result)))
        run.completed_at = utcnow()
    db.add(
        IncidentEvent(
            incident_id=incident.id, kind="analyzed", message=f"Analysis {result['phase']}"
        )
    )
    db.add(
        AuditLog(
            incident_id=incident.id,
            action="analysis.completed",
            detail={"run_id": run.id, "phase": result["phase"]},
        )
    )
    db.commit()
    db.refresh(run)
    return run


def decide(db: Session, proposal_id: int, decision: str, actor: str, reason: str) -> Report:
    proposal = db.get(Proposal, proposal_id)
    if not proposal:
        raise HTTPException(404, "Proposal not found")
    if proposal.status != "pending":
        raise HTTPException(409, "Proposal has already been decided")
    if decision == "approved" and proposal.risk == "blocked":
        raise HTTPException(403, "Unsafe proposal cannot be approved")
    run = db.get(AgentRun, proposal.run_id)
    incident = get_incident(db, proposal.incident_id)
    if run.checkpoint_thread_id:
        config = {
            "configurable": {"thread_id": run.checkpoint_thread_id},
            "recursion_limit": 16,
        }
        with workflow_graph(db) as graph:
            if "approval" not in graph.get_state(config).next:
                raise HTTPException(409, "Approval checkpoint is not pending")
            result = graph.invoke(Command(resume=decision), config)
    else:
        # Runs created before native checkpointing retain their saved relational state.
        result = GRAPH.invoke({**run.state, "decision": decision}, {"recursion_limit": 16})
    for step in result["steps"][len(run.state["steps"]) :]:
        db.add(AgentStep(run_id=run.id, **step))
    run.state = result
    run.status = result["phase"]
    run.completed_at = utcnow()
    proposal.status = decision
    incident.status = result["phase"]
    db.add(Approval(proposal_id=proposal.id, decision=decision, actor=actor, reason=reason))
    db.add(
        IncidentEvent(
            incident_id=incident.id, kind="approval", message=f"Proposal {decision} by {actor}"
        )
    )
    db.add(
        AuditLog(
            incident_id=incident.id,
            action="approval.decided",
            detail={"proposal_id": proposal.id, "decision": decision, "actor": actor},
        )
    )
    report = Report(incident_id=incident.id, content=_report(result))
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def _report(state: dict) -> dict:
    return {
        "mode": state.get("mode", "demo"),
        "severity": state.get("severity"),
        "hypothesis": state.get("hypothesis"),
        "confidence": state.get("confidence"),
        "sources": [
            {"source": item["source"], "title": item["title"]}
            for item in state.get("knowledge", [])
        ],
        "recommendation": state.get("action"),
        "risk": state.get("risk"),
        "decision": state.get("decision"),
        "outcome": state.get("outcome"),
        "status": state.get("phase"),
    }


def summary(db: Session) -> dict:
    counts = dict(db.execute(select(Incident.status, func.count()).group_by(Incident.status)).all())
    severities = dict(
        db.execute(select(Incident.severity, func.count()).group_by(Incident.severity)).all()
    )
    return {
        "incidents": sum(counts.values()),
        "by_status": counts,
        "by_severity": severities,
        "agent_runs": db.scalar(select(func.count(AgentRun.id))) or 0,
    }
