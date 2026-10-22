from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt


class IncidentState(TypedDict, total=False):
    mode: str
    incident_id: int
    title: str
    description: str
    service: str
    evidence: dict[str, Any]
    logs: list[str]
    error_rate: float
    knowledge: list[dict]
    steps: list[dict]
    severity: str
    hypothesis: str
    confidence: float
    action: str
    rationale: str
    risk: str
    blocked: bool
    decision: str
    phase: str
    outcome: str


def _step(state: IncidentState, agent: str, result: dict) -> list[dict]:
    return [*state.get("steps", []), {"agent": agent, "result": result}]


def triage(state: IncidentState) -> dict:
    severity = "critical" if state.get("error_rate", 0) >= 0.3 else "high"
    return {
        "severity": severity,
        "steps": _step(
            state,
            "triage",
            {"severity": severity, "service": state["service"], "mode": "simulated"},
        ),
    }


def investigation(state: IncidentState) -> dict:
    logs = state.get("logs", [])
    if state.get("mode") == "bedrock":
        from app.integrations.aws.bedrock import BedrockReasoner

        finding = BedrockReasoner().investigate(state["description"], logs)
        hypothesis, confidence = finding["hypothesis"], finding["confidence"]
    else:
        migration = any("column" in line.lower() for line in logs)
        hypothesis = (
            "Deployment references a database column before its migration ran"
            if migration
            else "HTTP 500 spike correlates with the deployment; cause needs further evidence"
        )
        confidence = 0.92 if migration else 0.45
    return {
        "hypothesis": hypothesis,
        "confidence": confidence,
        "steps": _step(
            state,
            "investigation",
            {"hypothesis": hypothesis, "confidence": confidence, "evidence": logs[:5]},
        ),
    }


def knowledge(state: IncidentState) -> dict:
    citations = [
        {"source": item["source"], "title": item["title"], "excerpt": item["excerpt"][:300]}
        for item in state.get("knowledge", [])
    ]
    return {"steps": _step(state, "knowledge", {"citations": citations})}


def supervisor(state: IncidentState) -> dict:
    route = "remediation" if state.get("confidence", 0) >= 0.6 else "escalation"
    return {
        "phase": route,
        "steps": _step(
            state, "supervisor", {"route": route, "reason": "Evidence confidence threshold 0.6"}
        ),
    }


def remediation(state: IncidentState) -> dict:
    action = (
        "Run the reviewed database migration, then redeploy or roll back v2.4.1 "
        "through the normal release pipeline"
    )
    rationale = "The error names a missing column and the deployment introduced its use."
    return {
        "action": action,
        "rationale": rationale,
        "risk": "medium",
        "steps": _step(
            state,
            "remediation",
            {
                "action": action,
                "rationale": rationale,
                "risk": "medium",
                "execution": "proposal only",
            },
        ),
    }


def security(state: IncidentState) -> dict:
    blocked = any(
        word in state.get("action", "").lower()
        for word in ("delete database", "drop table", "disable audit", "rm -rf")
    )
    return {
        "blocked": blocked,
        "phase": "blocked" if blocked else "awaiting_approval",
        "steps": _step(
            state,
            "security",
            {
                "blocked": blocked,
                "approval_required": True,
                "allowed_operations": ["recommend", "review"],
            },
        ),
    }


def validation(state: IncidentState) -> dict:
    decision = state.get("decision")
    if decision == "approved" and state.get("mode") == "bedrock":
        outcome = "Proposal approved. Recovery remains unverified; check live metrics after operator action."
        phase = "needs_verification"
    elif decision == "approved":
        outcome = "Simulated projection: if the reviewed migration succeeds, HTTP 500 errors should stop; no change was executed"
        phase = "complete"
    else:
        outcome = "Proposal rejected; incident remains unresolved"
        phase = "rejected"
    return {
        "outcome": outcome,
        "phase": phase,
        "steps": _step(
            state,
            "validation",
            {"outcome": outcome, "simulated": state.get("mode") != "bedrock", "decision": decision},
        ),
    }


def approval(state: IncidentState) -> dict:
    decision = interrupt(
        {"incident_id": state["incident_id"], "action": state["action"], "risk": state["risk"]}
    )
    if decision not in {"approved", "rejected"}:
        raise ValueError("Approval response must be approved or rejected")
    return {"decision": decision}


def escalation(state: IncidentState) -> dict:
    return {
        "phase": "escalated",
        "outcome": "Insufficient evidence; human investigation required",
        "steps": _step(state, "supervisor", {"escalated": True}),
    }


def entry(state: IncidentState) -> str:
    return "validation" if state.get("decision") in {"approved", "rejected"} else "triage"


def after_supervisor(state: IncidentState) -> str:
    return "remediation" if state["phase"] == "remediation" else "escalation"


def after_security(state: IncidentState) -> str:
    return "escalation" if state["blocked"] else END


def build_graph(checkpointer=None, *, interactive: bool = False):
    graph = StateGraph(IncidentState)
    for name, node in (
        ("triage", triage),
        ("investigation", investigation),
        ("knowledge", knowledge),
        ("supervisor", supervisor),
        ("remediation", remediation),
        ("security", security),
        ("validation", validation),
        ("escalation", escalation),
    ):
        graph.add_node(name, node)
    if interactive:
        graph.add_node("approval", approval)
        graph.add_edge("approval", "validation")
    graph.add_conditional_edges(START, entry)
    graph.add_edge("triage", "investigation")
    graph.add_edge("investigation", "knowledge")
    graph.add_edge("knowledge", "supervisor")
    graph.add_conditional_edges("supervisor", after_supervisor)
    graph.add_edge("remediation", "security")
    if interactive:
        graph.add_conditional_edges(
            "security", lambda state: "escalation" if state["blocked"] else "approval"
        )
    else:
        graph.add_conditional_edges("security", after_security)
    graph.add_edge("validation", END)
    graph.add_edge("escalation", END)
    return graph.compile(checkpointer=checkpointer)


GRAPH = build_graph()
