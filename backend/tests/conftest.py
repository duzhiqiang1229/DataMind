"""
Pytest configuration and fixtures for DataMind backend tests.

Two test tiers:
  1. Unit tests (no external deps) - run by default
  2. Integration tests (need PostgreSQL + Redis) - run with: pytest -m integration
"""
import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator

import pytest

# Ensure backend is on sys.path
backend_dir = str(Path(__file__).resolve().parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)


# ---------------------------------------------------------------------------
# Event loop
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Pure unit test fixtures (no DB / Redis required)
# ---------------------------------------------------------------------------
@pytest.fixture
def fake_user_data():
    """Return a dict suitable for creating a User object in tests."""
    return {
        "username": "testuser",
        "email": "test@datamind.com",
        "full_name": "Test User",
        "department": "QA",
        "status": "active",
        "hashed_password": "$2b$12$somehashvalue",
    }


# ---------------------------------------------------------------------------
# Integration test fixtures (require PostgreSQL + Redis)
# ---------------------------------------------------------------------------

# These are only imported when running integration tests to avoid
# failing at collection time when psycopg2 / asyncpg are not installed
# or the database is unreachable.

@pytest.fixture(scope="session")
def db_available() -> bool:
    """Check whether a PostgreSQL test database is reachable."""
    try:
        import psycopg2
        from app.core.config import settings
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            dbname=settings.DB_NAME,
            connect_timeout=3,
        )
        conn.close()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def redis_available() -> bool:
    """Check whether Redis is reachable."""
    try:
        import redis
        from app.core.config import settings
        r = redis.from_url(settings.redis_url, decode_responses=True)
        r.ping()
        r.close()
        return True
    except Exception:
        return False


@pytest.fixture
async def test_db_session(db_available) -> AsyncGenerator:
    """
    Provide an async DB session for integration tests.
    Creates tables at the start, drops them at the end.
    Skips the test if PostgreSQL is not available.
    """
    if not db_available:
        pytest.skip("PostgreSQL not available")

    from app.core.database import engine, Base, async_session
    import app.models  # register all models with Base.metadata

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session
        # Clean up specific test data by rolling back
        await session.rollback()

    # Drop all tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def test_client(test_db_session, redis_available):
    """
    Provide an httpx AsyncClient wired to the FastAPI app.
    Overrides get_db to use the test session.
    Skips if Redis is not available.
    """
    if not redis_available:
        pytest.skip("Redis not available")

    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.core.database import get_db

    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
