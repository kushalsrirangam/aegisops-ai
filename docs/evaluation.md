# Evaluation

The versioned [synthetic cases](../backend/app/evaluation/cases.json) exercise the deterministic demo graph. Run from `backend/` after installing `.[dev]`:

```shell
python -m app.evaluation.run
python -m pytest -q tests/test_evaluation.py
```

The runner is read-only: it invokes the graph in memory and prints JSON. Each case defines its expected hypothesis category, confidence band (high means at least 0.6), route, citation source IDs, proposal presence, and whether the hypothesis may claim a deployment. A case passes only if every check passes. Citation checks verify that supplied source IDs survive in the trace; they do **not** assess retrieval relevance or source truth.

## Deterministic demo results, 2026-10-23

| Check | Initial baseline | After evidence-gating fix |
| --- | ---: | ---: |
| Entire case | 1 / 6 | 6 / 6 |
| Hypothesis category | 4 / 6 | 6 / 6 |
| Confidence band | 4 / 6 | 6 / 6 |
| Route | 4 / 6 | 6 / 6 |
| Citation source IDs | 6 / 6 | 6 / 6 |
| Proposal presence | 4 / 6 | 6 / 6 |
| Deployment claim supported by case | 1 / 6 | 6 / 6 |

Initially, cache timeout, upstream 503, and no-evidence cases escalated but asserted an unsupported deployment correlation. A benign `column_name` mention and a missing-column error without release evidence both triggered a 0.92-confidence migration proposal. The demo investigator now requires a missing-column error, a positive deployment event, and a pending migration to make that specific high-confidence proposal. Otherwise it reports uncertainty and escalates. Tests also cover negated deployment and migration statements, and the API preserves an explicitly empty log list instead of substituting synthetic logs.

The test now requires all six current cases and all checks to pass. The initial 1/6 score remains here as a historical comparison. A green CI run establishes this small benchmark passes; it does **not** establish general incident accuracy.

This set has six hand-written synthetic cases, no independent labels, and no live telemetry. The conservative text rules can miss different log formats or correlated events; they do not establish causation. The confidence values are fixed by the demo logic and are not calibrated probabilities. This benchmark does not measure Bedrock accuracy, semantic retrieval quality, production security, or real recovery. Those need a larger labeled incident set, human review, and validation against approved live or replayed telemetry. GitHub Actions separately runs API tests and PostgreSQL integration tests for persistence, checkpoints, and approvals.
