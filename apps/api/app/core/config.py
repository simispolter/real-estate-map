from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Real Estate Intelligence API"
    app_env: str = Field(default="development", alias="APP_ENV")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    api_v1_prefix: str = "/api/v1"
    debug: bool = Field(default=False, alias="DEBUG")
    database_url: str = Field(
        default=(
            "postgresql+asyncpg://real_estate:real_estate@localhost:5432/real_estate_map"
        ),
        alias="DATABASE_URL",
    )
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")
    slow_query_threshold_ms: int = Field(default=75, alias="SLOW_QUERY_THRESHOLD_MS")
    request_timing_threshold_ms: int = Field(default=150, alias="REQUEST_TIMING_THRESHOLD_MS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
