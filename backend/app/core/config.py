"""
Application configuration via pydantic-settings.
Reads from .env file and environment variables.
"""
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # -------------------- App --------------------
    APP_NAME: str = "AI Resource Hub"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # -------------------- Database --------------------
    POSTGRES_USER: str = "arh_admin"
    POSTGRES_PASSWORD: str = "arh_secret"
    POSTGRES_DB: str = "ai_resource_hub"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    @property
    def DATABASE_URL(self) -> str:
        """Async URL — uses psycopg 3 native async (no asyncpg needed)."""
        return (
            f"postgresql+psycopg_async://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Sync URL for Alembic migrations (uses psycopg 3 driver)."""
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # -------------------- Redis --------------------
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"

    # -------------------- JWT --------------------
    JWT_SECRET_KEY: str = "change-me-to-a-random-64-char-string"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # -------------------- Vault Encryption --------------------
    VAULT_ENCRYPTION_KEY: str = "change-me-to-a-32-byte-hex-string"

    # -------------------- Monitoring (Prometheus + Grafana) --------------------
    PROMETHEUS_URL: str = "http://localhost:9090"
    GRAFANA_URL: str = "http://localhost:3000"

    # -------------------- Pi Agent (container provisioning) --------------------
    PI_COMMAND: str = "pi"
    PI_TIMEOUT: int = 300  # seconds — provisioning may take a while
    # DeepSeek API (OpenAI-compatible format for Pi's LLM backend)
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # -------------------- Ansible --------------------
    ANSIBLE_INVENTORY_PATH: str = "./ansible/inventory"
    ANSIBLE_PLAYBOOK_PATH: str = "./ansible/playbooks"

    # -------------------- CORS --------------------
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]


settings = Settings()
