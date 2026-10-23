import math
from datetime import UTC, datetime, timedelta
from typing import Protocol

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError


class CloudProvider(Protocol):
    def logs(self, service: str) -> list[str]: ...
    def error_rate(self, service: str) -> float: ...


class MockCloudProvider:
    def logs(self, service: str) -> list[str]:
        return [
            f"{service}: HTTP 500 after deploy v2.4.1",
            "DatabaseError: column customer_tier does not exist",
            "Migration 2026_10_22_add_customer_tier pending",
        ]

    def error_rate(self, service: str) -> float:
        return 0.37


class CloudWatchProvider:
    """Read-only calls. IAM policy is documented under infrastructure."""

    def __init__(
        self,
        region: str,
        log_group_prefix: str = "/ecs/aegisops/",
        metric_namespace: str = "",
        metric_name: str = "ErrorRate",
        metric_dimension_name: str = "Service",
    ) -> None:
        timeout = Config(connect_timeout=3, read_timeout=8, retries={"max_attempts": 1})
        self.logs_client = boto3.client("logs", region_name=region, config=timeout)
        self.metrics_client = boto3.client("cloudwatch", region_name=region, config=timeout)
        self.log_group_prefix = log_group_prefix
        self.metric_namespace = metric_namespace
        self.metric_name = metric_name
        self.metric_dimension_name = metric_dimension_name

    def logs(self, service: str) -> list[str]:
        if not service.replace("-", "").isalnum():
            raise ValueError("Invalid service name")
        try:
            response = self.logs_client.filter_log_events(
                logGroupName=f"{self.log_group_prefix}{service}", limit=50
            )
            return [event["message"] for event in response.get("events", [])]
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError("CloudWatch logs unavailable") from exc

    def error_rate(self, service: str) -> float:
        if not self.metric_namespace:
            raise RuntimeError("CloudWatch error-rate metric is not configured")
        if not service.replace("-", "").isalnum():
            raise ValueError("Invalid service name")
        end = datetime.now(UTC)
        try:
            response = self.metrics_client.get_metric_statistics(
                Namespace=self.metric_namespace,
                MetricName=self.metric_name,
                Dimensions=[{"Name": self.metric_dimension_name, "Value": service}],
                StartTime=end - timedelta(minutes=5),
                EndTime=end,
                Period=60,
                Statistics=["Average"],
                Unit="Percent",
            )
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError("CloudWatch metrics unavailable") from exc
        points = response.get("Datapoints", [])
        if not points:
            raise RuntimeError("No recent CloudWatch error-rate datapoints")
        percent = max(points, key=lambda point: point["Timestamp"])["Average"]
        if not isinstance(percent, (int, float)) or not math.isfinite(percent) or not 0 <= percent <= 100:
            raise RuntimeError("CloudWatch error-rate datapoint is invalid")
        return percent / 100
