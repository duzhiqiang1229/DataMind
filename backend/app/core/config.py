"""Application configuration via Pydantic Settings."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """DataMind configuration, loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    APP_NAME: str = "DataMind"
    APP_VERSION: str = "1.1.3"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    BOOTSTRAP_ADMIN: bool = False
    INITIAL_ADMIN_USERNAME: str = "admin"
    INITIAL_ADMIN_PASSWORD: str = ""
    EXECUTOR_URL: str = ""
    EXECUTOR_TOKEN: str = ""
    LINEAGE_EVENT_TOKEN: str = ""
    CUBE_API_SECRET: str = ""

    # --- PostgreSQL ---
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 5432
    DB_USER: str = "datamind"
    DB_PASSWORD: str = "datamind"
    DB_NAME: str = "datamind"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def database_url_sync(self) -> str:
        """Sync URL for Alembic migrations."""
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # --- Redis ---
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    @property
    def redis_url(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # --- JWT ---
    JWT_SECRET_KEY: str = "change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Encryption ---
    ENCRYPTION_KEY: str = ""

    # --- Airflow Polling ---
    AIRFLOW_POLL_INTERVAL_SECONDS: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def validate_production_settings() -> None:
    """Fail fast when a production process starts with unsafe key material."""
    if settings.APP_ENV.lower() != "production":
        return

    errors: list[str] = []
    if (
        len(settings.JWT_SECRET_KEY) < 24
        or settings.JWT_SECRET_KEY in {"change-in-production", "your-secret-key-change-in-production"}
    ):
        errors.append("JWT_SECRET_KEY must be a non-default secret of at least 24 characters")

    if not settings.ENCRYPTION_KEY:
        errors.append("ENCRYPTION_KEY is required")
    else:
        try:
            from cryptography.fernet import Fernet
            Fernet(settings.ENCRYPTION_KEY.encode())
        except (ValueError, TypeError):
            errors.append("ENCRYPTION_KEY must be a valid Fernet key")

    if settings.BOOTSTRAP_ADMIN and len(settings.INITIAL_ADMIN_PASSWORD) < 12:
        errors.append("INITIAL_ADMIN_PASSWORD must contain at least 12 characters")
    if settings.EXECUTOR_URL and len(settings.EXECUTOR_TOKEN) < 24:
        errors.append("EXECUTOR_TOKEN must contain at least 24 characters")
    if settings.LINEAGE_EVENT_TOKEN and len(settings.LINEAGE_EVENT_TOKEN) < 24:
        errors.append("LINEAGE_EVENT_TOKEN must contain at least 24 characters")
    if len(settings.CUBE_API_SECRET) < 24:
        errors.append("CUBE_API_SECRET must contain at least 24 characters")

    if errors:
        raise RuntimeError("Unsafe production configuration: " + "; ".join(errors))
