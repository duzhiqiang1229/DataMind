"""DataMind Backend - Application Entry Point"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import settings
from app.core.database import engine, Base
from app.core.redis import redis_client
from app.api.router import api_router
from app.utils.task_scheduler import init_scheduler, shutdown_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup & shutdown."""
    # --- Startup ---
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode")

    # Create database tables (use Alembic in production)
    if settings.APP_DEBUG:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created (debug mode)")

    # Connect Redis
    await redis_client.ping()
    logger.info("Redis connected")

    # Start Airflow status polling scheduler
    init_scheduler()
    logger.info("Task status polling scheduler started")

    yield

    # --- Shutdown ---
    shutdown_scheduler()
    await redis_client.close()
    await engine.dispose()
    logger.info(f"{settings.APP_NAME} stopped")


app = FastAPI(
    title=settings.APP_NAME,
    description="DataMind Enterprise Data Platform API",
    version="1.0.0",
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
from app.utils.operation_log_middleware import OperationLogMiddleware
app.add_middleware(OperationLogMiddleware)

# Register API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.APP_NAME}
