"""Run the versioned synthetic incident benchmark without writing application data."""

import json
from pathlib import Path

from app.orchestration.graph import GRAPH

CASES = Path(__file__).with_name("cases.json")
CHECKS = ("hypothesis", "confidence", "phase", "citations", "proposal", "deployment_claim")


def evaluate_case(case: dict) -> dict:
    state = {key: value for key, value in case.items() if key not in {"id", "expected"}}
    state["mode"] = "demo"
    state["steps"] = []
    result = GRAPH.invoke(state, {"recursion_limit": 16})
    citations = [
        citation["source"]
        for step in result["steps"]
        if step["agent"] == "knowledge"
        for citation in step["result"]["citations"]
    ]
    confidence = result["confidence"]
    observed = {
        "hypothesis": (
            "migration" if "database column" in result["hypothesis"].lower() else "uncertain"
        ),
        "confidence": "high" if confidence >= 0.6 else "low",
        "phase": result["phase"],
        "citations": citations,
        "proposal": any(step["agent"] == "remediation" for step in result["steps"]),
        "deployment_claim": "deployment" in result["hypothesis"].lower(),
    }
    checks = {name: observed[name] == case["expected"][name] for name in CHECKS}
    return {
        "id": case["id"],
        "checks": checks,
        "passed": all(checks.values()),
        "observed": {**observed, "confidence_score": confidence, "hypothesis_text": result["hypothesis"]},
    }


def run_suite(cases: list[dict] | None = None) -> dict:
    cases = json.loads(CASES.read_text(encoding="utf-8")) if cases is None else cases
    results = [evaluate_case(case) for case in cases]
    return {
        "mode": "deterministic_demo",
        "case_count": len(results),
        "passed_cases": sum(item["passed"] for item in results),
        "check_pass_counts": {
            name: sum(item["checks"][name] for item in results) for name in CHECKS
        },
        "results": results,
    }


if __name__ == "__main__":
    print(json.dumps(run_suite(), indent=2))
