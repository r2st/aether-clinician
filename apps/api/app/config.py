"""Application settings, loaded from environment via pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration. Values come from environment / .env files."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application ---
    app_env: Literal["development", "staging", "production", "test"] = "development"
    app_secret_key: str = "dev-insecure-secret-change-me"
    app_debug: bool = True
    demo_mode: bool = True

    # --- Database ---
    database_url: str = "postgresql+asyncpg://aether:aether@localhost:5432/aether_clinician"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Anthropic / extraction ---
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_max_tokens: int = 4096
    extraction_prompt_version: str = "v1.0"

    # --- Storage ---
    storage_backend: Literal["local", "s3"] = "local"
    local_storage_dir: str = "./storage"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_name: str = "aether-documents"

    # --- OCR ---
    tesseract_cmd: str = "/usr/bin/tesseract"

    # --- Auth ---
    jwt_access_ttl_minutes: int = 15
    jwt_refresh_ttl_days: int = 7
    bcrypt_rounds: int = 12
    jwt_algorithm: str = "HS256"

    # --- Uploads ---
    max_upload_bytes: int = 20 * 1024 * 1024  # 20 MB
    confirmation_confidence_threshold: float = 0.85
    ocr_fallback_threshold: float = 0.50

    # --- CORS ---
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


settings = get_settings()
