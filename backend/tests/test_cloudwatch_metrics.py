"""Read-only CloudWatch metric mapping and evidence provenance."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from app.core.config import get_settings
from app.integrations.aws.provider import CloudWatchProvider
from app.orchestration.graph import triage
from app.services.incidents import analyze, create_incident


@patch("app.integrations.aws.provider.boto3.client")
def test_cloudwatch_latest_percent_datapoint_becomes_fraction(client_factory):
    metrics = Mock()
    client_factory.side_effect = [Mock(), metrics]
    now = datetime.now(UTC)
    metrics.get_metric_statistics.return_value = {
        "Datapoints": [
            {"Timestamp": now, "Average": 37.0},
            {"Timestamp": now - timedelta(minutes=1), "Average": 12.0},
        ]
    }
    provider = CloudWatchProvider("us-east-1", metric_namespace="AegisOps")

    assert provider.error_rate("checkout-api") == 0.37
    request = metrics.get_metric_statistics.call_args.kwargs
    assert request["Namespace"] == "AegisOps"
    assert request["MetricName"] == "ErrorRate"
    assert request["Dimensions"] == [{"Name": "Service", "Value": "checkout-api"}]
    assert request["Unit"] == "Percent"
    assert request["Period"] == 60


@patch("app.integrations.aws.provider.boto3.client")
def test_cloudwatch_missing_or_invalid_metric_is_not_treated_as_zero(client_factory):
    metrics = Mock()
    client_factory.side_effect = [Mock(), metrics]
    provider = CloudWatchProvider("us-east-1", metric_namespace="AegisOps")
    metrics.get_metric_statistics.return_value = {"Datapoints": []}
    with pytest.raises(RuntimeError, match="No recent"):
        provider.error_rate("checkout-api")

    metrics.get_metric_statistics.return_value = {
        "Datapoints": [{"Timestamp": datetime.now(UTC), "Average": 145.0}]
    }
    with pytest.raises(RuntimeError, match="invalid"):
        provider.error_rate("checkout-api")


def test_triage_records_metric_source_without_fabricating_unavailable_rate():
    result = triage(
        {
            "service": "checkout-api",
            "mode": "bedrock",
            "error_rate": None,
            "metric_source": "unavailable",
            "steps": [],
        }
    )
    assert result["steps"][0]["result"] == {
        "severity": "high",
        "service": "checkout-api",
        "mode": "bedrock",
        "error_rate": None,
        "metric_source": "unavailable",
    }


def test_bedrock_analysis_uses_configured_cloudwatch_metric(db, monkeypatch):
    incident = create_incident(
        db,
        "Checkout errors after deploy",
        "Requests fail with missing column after deployment",
        "checkout-api",
        {"logs": ["DatabaseError: column customer_tier does not exist"]},
    )
    incident.mode = "bedrock"
    db.commit()
    cloud = Mock()
    cloud.error_rate.return_value = 0.37
    monkeypatch.setattr(get_settings(), "aws_error_rate_metric_namespace", "AegisOps")
    monkeypatch.setattr("app.services.incidents.CloudWatchProvider", lambda *args, **kwargs: cloud)
    reasoner = Mock()
    reasoner.investigate.return_value = {"hypothesis": "Missing migration", "confidence": 0.92}
    monkeypatch.setattr("app.integrations.aws.bedrock.BedrockReasoner", lambda: reasoner)

    run = analyze(db, incident.id)

    cloud.error_rate.assert_called_once_with("checkout-api")
    assert run.state["metric_source"] == "CloudWatch"
    assert run.state["error_rate"] == 0.37
    assert run.state["steps"][0]["result"]["metric_source"] == "CloudWatch"
    assert run.status == "awaiting_approval"
