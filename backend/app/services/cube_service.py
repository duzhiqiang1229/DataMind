"""Cube metrics service: meta + query + health."""
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.services.component_service import get_cube_client


async def get_meta(db: AsyncSession) -> dict:
    """Get Cube meta: available cubes, dimensions, measures."""
    try:
        cube = await get_cube_client(db)
        return await cube.get_meta()
    except RuntimeError as e:
        raise RuntimeError(f"Cube not configured: {e}")


async def load_data(db: AsyncSession, query: dict) -> dict:
    """Execute a Cube query and return results."""
    try:
        cube = await get_cube_client(db)
        return await cube.load(query)
    except RuntimeError as e:
        raise RuntimeError(f"Cube not configured: {e}")


async def health_check(db: AsyncSession) -> bool:
    """Check Cube connectivity."""
    try:
        cube = await get_cube_client(db)
        return await cube.health_check()
    except RuntimeError:
        return False
