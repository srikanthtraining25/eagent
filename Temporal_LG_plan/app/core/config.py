"""
Centralized configuration loaded from environment variables / .env file.

All settings are configurable via the .env file. See .env.example for defaults.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Root directory of the app package
APP_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = APP_DIR.parent


class AppSettings(BaseSettings):
    """General application settings."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    name: str = Field(default="enterprise-agent", alias="APP_NAME")
    version: str = Field(default="1.0.0", alias="APP_VERSION")
    host: str = Field(default="0.0.0.0", alias="APP_HOST")
    port: int = Field(default=8000, alias="APP_PORT")
    debug: bool = Field(default=False, alias="APP_DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")


class LLMSettings(BaseSettings):
    """LLM provider settings."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    provider: str = Field(default="openai", alias="LLM_PROVIDER")
    model: str = Field(default="gpt-4o", alias="LLM_MODEL")
    temperature: float = Field(default=0.0, alias="LLM_TEMPERATURE")
    max_tokens: int = Field(default=4096, alias="LLM_MAX_TOKENS")
    api_key: str = Field(default="", alias="OPENAI_API_KEY")


class TemporalSettings(BaseSettings):
    """Temporal server and workflow settings."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = Field(default="localhost", alias="TEMPORAL_HOST")
    port: int = Field(default=7233, alias="TEMPORAL_PORT")
    namespace: str = Field(default="default", alias="TEMPORAL_NAMESPACE")
    task_queue: str = Field(default="enterprise-agent", alias="TEMPORAL_TASK_QUEUE")
    workflow_execution_timeout: int = Field(
        default=300, alias="TEMPORAL_WORKFLOW_EXECUTION_TIMEOUT"
    )
    activity_start_to_close_timeout: int = Field(
        default=120, alias="TEMPORAL_ACTIVITY_START_TO_CLOSE_TIMEOUT"
    )
    activity_retry_max_attempts: int = Field(
        default=3, alias="TEMPORAL_ACTIVITY_RETRY_MAX_ATTEMPTS"
    )

    @property
    def server_url(self) -> str:
        return f"{self.host}:{self.port}"


class RedisSettings(BaseSettings):
    """Redis connection settings."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = Field(default="localhost", alias="REDIS_HOST")
    port: int = Field(default=6379, alias="REDIS_PORT")
    db: int = Field(default=0, alias="REDIS_DB")
    password: Optional[str] = Field(default=None, alias="REDIS_PASSWORD")
    url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    @field_validator("password", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: str | None) -> str | None:
        if v == "":
            return None
        return v

    @property
    def connection_url(self) -> str:
        """Build connection URL from components if REDIS_URL not explicitly set."""
        if self.url and self.url != "redis://localhost:6379/0":
            return self.url
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


class PostgresSettings(BaseSettings):
    """PostgreSQL settings (used by Temporal backend)."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = Field(default="localhost", alias="POSTGRES_HOST")
    port: int = Field(default=5432, alias="POSTGRES_PORT")
    db: str = Field(default="temporal", alias="POSTGRES_DB")
    user: str = Field(default="temporal", alias="POSTGRES_USER")
    password: str = Field(default="temporal", alias="POSTGRES_PASSWORD")

    @property
    def dsn(self) -> str:
        return (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.db}"
        )


class A2ASettings(BaseSettings):
    """FastA2A server and client settings."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    agent_name: str = Field(default="enterprise-agent", alias="A2A_AGENT_NAME")
    agent_description: str = Field(
        default="Enterprise AI Agent — handles KB queries, actions, and delegations",
        alias="A2A_AGENT_DESCRIPTION",
    )
    agent_version: str = Field(default="1.0.0", alias="A2A_AGENT_VERSION")
    base_url: str = Field(default="http://localhost:8000", alias="A2A_BASE_URL")

    # Client (outbound)
    client_timeout: int = Field(default=30, alias="A2A_CLIENT_TIMEOUT")
    client_max_retries: int = Field(default=3, alias="A2A_CLIENT_MAX_RETRIES")

    # External agent registry
    external_agent_urls: list[str] = Field(
        default_factory=list, alias="A2A_EXTERNAL_AGENT_URLS"
    )

    @field_validator("external_agent_urls", mode="before")
    @classmethod
    def parse_comma_separated(cls, v: str | list) -> list[str]:
        if isinstance(v, str):
            return [u.strip() for u in v.split(",") if u.strip()]
        return v


class KBSettings(BaseSettings):
    """Knowledge Base / RAG settings."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    collection_name: str = Field(default="enterprise_kb", alias="KB_COLLECTION_NAME")
    embedding_model: str = Field(
        default="text-embedding-3-small", alias="KB_EMBEDDING_MODEL"
    )
    chunk_size: int = Field(default=1000, alias="KB_CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, alias="KB_CHUNK_OVERLAP")
    top_k: int = Field(default=5, alias="KB_TOP_K")


class ObservabilitySettings(BaseSettings):
    """Observability / tracing settings."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    otel_enabled: bool = Field(default=True, alias="OTEL_ENABLED")
    otel_service_name: str = Field(
        default="enterprise-agent", alias="OTEL_SERVICE_NAME"
    )
    otel_exporter_endpoint: str = Field(
        default="http://localhost:6006", alias="OTEL_EXPORTER_ENDPOINT"
    )
    phoenix_enabled: bool = Field(default=True, alias="PHOENIX_ENABLED")
    phoenix_project_name: str = Field(
        default="enterprise-agent", alias="PHOENIX_PROJECT_NAME"
    )


class Settings(BaseSettings):
    """
    Root settings object — aggregates all sub-settings.

    Usage:
        from app.core.config import get_settings
        settings = get_settings()
        settings.temporal.server_url  # "localhost:7233"
        settings.redis.connection_url # "redis://localhost:6379/0"
    """

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app: AppSettings = Field(default_factory=AppSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    temporal: TemporalSettings = Field(default_factory=TemporalSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    a2a: A2ASettings = Field(default_factory=A2ASettings)
    kb: KBSettings = Field(default_factory=KBSettings)
    observability: ObservabilitySettings = Field(
        default_factory=ObservabilitySettings
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance (singleton)."""
    return Settings()
