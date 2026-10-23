from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./aegisops.db"
    app_mode: str = "demo"
    aws_region: str = "us-east-1"
    aws_error_rate_metric_namespace: str = ""
    aws_error_rate_metric_name: str = "ErrorRate"
    aws_error_rate_metric_dimension_name: str = "Service"
    bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    cors_origins: str = "http://localhost:5173"

    def model_post_init(self, __context: object, /) -> None:
        if self.app_mode not in {"demo", "bedrock"}:
            raise ValueError("APP_MODE must be demo or bedrock")
        if self.aws_error_rate_metric_namespace and (
            ":" in self.aws_error_rate_metric_namespace
            or not self.aws_error_rate_metric_name.strip()
            or not self.aws_error_rate_metric_dimension_name.strip()
        ):
            raise ValueError("CloudWatch error-rate metric mapping is invalid")


@lru_cache
def get_settings() -> Settings:
    return Settings()
