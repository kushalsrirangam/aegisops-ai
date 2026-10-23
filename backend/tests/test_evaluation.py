from app.evaluation.run import run_suite


def test_synthetic_benchmark_records_known_false_positives():
    report = run_suite()
    assert report["case_count"] == 6
    assert report["passed_cases"] == 1
    assert report["check_pass_counts"]["citations"] == 6
    assert report["check_pass_counts"]["deployment_claim"] == 1
    failures = {item["id"] for item in report["results"] if not item["passed"]}
    assert failures == {
        "cache_timeout", "upstream_unavailable", "no_evidence",
        "benign_column_mention", "missing_column_without_deploy"
    }
    for item in report["results"]:
        assert set(item["checks"]) == {
            "hypothesis", "confidence", "phase", "citations", "proposal", "deployment_claim"
        }
