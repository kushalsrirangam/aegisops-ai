from app.evaluation.run import run_suite


def test_synthetic_benchmark_meets_all_case_expectations():
    report = run_suite()
    assert report["case_count"] == 6
    assert report["passed_cases"] == 6
    assert all(count == 6 for count in report["check_pass_counts"].values())
    failures = {item["id"] for item in report["results"] if not item["passed"]}
    assert failures == set()
    for item in report["results"]:
        assert set(item["checks"]) == {
            "hypothesis", "confidence", "phase", "citations", "proposal", "deployment_claim"
        }


def test_challenge_set_passes_with_correlated_evidence():
    report = run_suite(suite="challenge")
    assert report["case_count"] == 8
    assert report["passed_cases"] == 8
    failures = {item["id"] for item in report["results"] if not item["passed"]}
    assert failures == set()
    assert report["proposal_confusion"] == {
        "true_positive": 2,
        "false_positive": 0,
        "true_negative": 6,
        "false_negative": 0,
    }
