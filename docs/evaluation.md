# Evaluation

The versioned [synthetic cases](../backend/app/evaluation/cases.json) exercise the deterministic demo graph. Run from `backend/` after installing `.[dev]`:

```shell
python -m app.evaluation.run
python -m pytest -q tests/test_evaluation.py
```

The runner is read-only: it invokes the graph in memory and prints JSON. Each case defines its expected hypothesis category, confidence band (high means at least 0.6), route, citation source IDs, proposal presence, and whether the hypothesis may claim a deployment. A case passes only if every check passes. Citation checks verify that supplied source IDs survive in the trace; they do **not** assess retrieval relevance or source truth.

## Baseline: deterministic demo, 2026-10-23

| Check | Passed / total |
| --- | ---: |
| Entire case | 1 / 6 |
| Hypothesis category | 4 / 6 |
| Confidence band | 4 / 6 |
| Route | 4 / 6 |
| Citation source IDs | 6 / 6 |
| Proposal presence | 4 / 6 |
| Deployment claim supported by case | 1 / 6 |

The missing-column-after-deploy case passes. Cache timeout, upstream 503, and no-evidence cases escalate without a proposal, but their hypothesis still asserts a deployment correlation that their evidence does not support. A benign analytics log mentioning `column_name` and a missing-column error without release evidence both trigger a 0.92-confidence migration hypothesis and a migration proposal. These are false positives in this benchmark. Human review and the proposal-only policy prevent automatic remediation, but they do not make the analysis accurate.

The test intentionally verifies these observed weaknesses so changes cannot silently alter the baseline. A green CI run means the benchmark ran and the measurements match the documented baseline; it does **not** mean all cases passed. If the investigation logic improves, update the expectations and documented results together.

This set has six hand-written synthetic cases, no independent labels, and no live telemetry. The confidence values are fixed by the demo logic and are not calibrated probabilities. It does not measure Bedrock accuracy, semantic retrieval quality, production security, or real recovery. Those need a larger labeled incident set, human review, and validation against approved live or replayed telemetry. GitHub Actions separately runs API tests and PostgreSQL integration tests for persistence, checkpoints, and approvals.
