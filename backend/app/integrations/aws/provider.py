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

    def __init__(self, region: str, log_group_prefix: str = "/ecs/aegisops/") -> None:
        timeout = Config(connect_timeout=3, read_timeout=8, retries={"max_attempts": 1})
        self.logs_client = boto3.client("logs", region_name=region, config=timeout)
        self.metrics_client = boto3.client("cloudwatch", region_name=region, config=timeout)
        self.log_group_prefix = log_group_prefix

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
        # A deployment must define the metric namespace/dimensions before this can return data.
        raise RuntimeError("CloudWatch metric mapping is not configured")
