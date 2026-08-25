"""DataMind Backend - Application Entry Point"""
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import settings, validate_production_settings
from app.core.database import engine, Base
from app.core.redis import redis_client
from app.api.router import api_router
from app.utils.operation_log_middleware import OperationLogMiddleware


async def _sync_airflow_runtime_lineage() -> None:
    """Periodically pull completed Airflow tasks and their runtime lineage."""
    from app.core.database import async_session
    from app.services.airflow_service import sync_dag_runs

    async with async_session() as db:
        try:
            await sync_dag_runs(db)
        except Exception as exc:
            logger.warning(f"Periodic Airflow runtime lineage sync failed: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup & shutdown."""
    # --- Startup ---
    validate_production_settings()
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode")

    # Create database tables (use Alembic in production)
    if settings.APP_DEBUG:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created (debug mode)")

    # Connect Redis
    await redis_client.ping()
    logger.info("Redis connected")

    scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(
        _sync_airflow_runtime_lineage, "interval", minutes=5,
        id="airflow_runtime_lineage_sync", replace_existing=True,
        coalesce=True, max_instances=1,
        next_run_time=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    scheduler.start()
    logger.info("Airflow runtime lineage sync scheduled every 5 minutes")

    yield

    # --- Shutdown ---
    scheduler.shutdown(wait=False)
    await redis_client.close()
    await engine.dispose()
    logger.info(f"{settings.APP_NAME} stopped")


app = FastAPI(
    title=settings.APP_NAME,
    description="DataMind Enterprise Data Platform API",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.APP_DEBUG else None,
    redoc_url="/redoc" if settings.APP_DEBUG else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.APP_DEBUG else ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Operation logging middleware (logs POST/PUT/DELETE operations)
app.add_middleware(OperationLogMiddleware)

# Register API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.APP_NAME, "version": settings.APP_VERSION}
