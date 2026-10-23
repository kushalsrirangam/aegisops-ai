# Evaluation

The versioned [synthetic cases](../backend/app/evaluation/cases.json) exercise the deterministic demo graph. Run from `backend/` after installing `.[dev]`:

```shell
python -m app.evaluation.run
python -m app.evaluation.run --suite challenge
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

## Separate challenge set

Eight additional [challenge cases](../backend/app/evaluation/challenge_cases.json) were written after the evidence-gating rule. They vary log phrasing, service identity, event recency, and migration state. They are not a blind or externally labeled holdout: the author knew the rule. They are kept separate from the six development cases so later rule changes can be checked against both sets.

The initial rule passed **4/8 challenge cases**. For the decision to propose a migration review, it had **1 true positive, 3 false positives, 3 true negatives, and 1 false negative**. The false positives arose when a deployment belonged to another service, was a week old, or a previously pending migration later completed. The false negative used “release ... rolled out” rather than the recognized deployment wording.

The current rule passes **8/8 challenge cases** with **2 true positives, 0 false positives, 6 true negatives, and 0 false negatives** on this set. It requires a deployment event before the missing-column error, matches service tags when present, rejects explicitly stale deployment lines, recognizes the release rollout wording, and uses the last reported status for a migration naming the missing column. The challenge test now requires these cases to pass. The previous 4/8 result remains above as a historical comparison.

Both sets contain hand-written synthetic cases, no independent labels, and no live telemetry. The parser assumes the supplied log list is in event order, recognizes only a small set of service tags and recency phrases, and cannot establish causation from unstructured logs. The confidence values are fixed by the demo logic and are not calibrated probabilities. These benchmarks do not measure Bedrock accuracy, semantic retrieval quality, production security, or real recovery. Those need a larger labeled incident set, human review, and validation against approved live or replayed telemetry. GitHub Actions separately runs API tests and PostgreSQL integration tests for persistence, checkpoints, and approvals.
