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


def test_challenge_set_records_current_limits():
    report = run_suite(suite="challenge")
    assert report["case_count"] == 8
    assert report["passed_cases"] == 4
    failures = {item["id"] for item in report["results"] if not item["passed"]}
    assert failures == {
        "release_rollout_wording",
        "other_service_deployment",
        "stale_deployment",
        "migration_later_completed",
    }
    assert report["proposal_confusion"] == {
        "true_positive": 1,
        "false_positive": 3,
        "true_negative": 3,
        "false_negative": 1,
    }
