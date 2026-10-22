from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./aegisops.db"
    app_mode: str = "demo"
    aws_region: str = "us-east-1"
    bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    cors_origins: str = "http://localhost:5173"

    def model_post_init(self, __context: object, /) -> None:
        if self.app_mode not in {"demo", "bedrock"}:
            raise ValueError("APP_MODE must be demo or bedrock")


@lru_cache
def get_settings() -> Settings:
    return Settings()
