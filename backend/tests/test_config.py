"""
Unit tests for app.core.config: Settings loading and computed properties.

No external services required.
"""
from app.core.config import Settings


class TestSettings:
    def test_database_url_contains_asyncpg(self):
        s = Settings(_env_file=None)
        assert "postgresql+asyncpg://" in s.database_url

    def test_database_url_sync_contains_psycopg2(self):
        s = Settings(_env_file=None)
        assert "postgresql+psycopg2://" in s.database_url_sync

    def test_redis_url_format_no_password(self):
        s = Settings(_env_file=None, REDIS_PASSWORD="")
        assert s.redis_url == f"redis://{s.REDIS_HOST}:{s.REDIS_PORT}/{s.REDIS_DB}"

    def test_redis_url_format_with_password(self):
        s = Settings(_env_file=None, REDIS_PASSWORD="secret")
        assert s.redis_url == f"redis://:secret@{s.REDIS_HOST}:{s.REDIS_PORT}/{s.REDIS_DB}"

    def test_defaults(self):
        s = Settings(_env_file=None)
        assert s.APP_NAME == "DataMind"
        assert s.APP_ENV == "development"
        assert s.APP_DEBUG is True
        assert s.APP_PORT == 8000
        assert s.JWT_ALGORITHM == "HS256"
        assert s.JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 120
        assert s.JWT_REFRESH_TOKEN_EXPIRE_DAYS == 7

    def test_database_url_includes_credentials(self):
        s = Settings(
            _env_file=None,
            DB_USER="myuser",
            DB_PASSWORD="mypass",
            DB_HOST="myhost",
            DB_PORT=9999,
            DB_NAME="mydb",
        )
        url = s.database_url
        assert "myuser" in url
        assert "mypass" in url
        assert "myhost" in url
        assert "9999" in url
        assert "mydb" in url
