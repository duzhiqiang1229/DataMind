"""OpenMetadata governance service: catalog + lineage + search."""
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.services.component_service import get_openmetadata_client


async def list_databases(db: AsyncSession, limit: int = 100) -> list[dict]:
    """List all registered databases in OpenMetadata."""
    try:
        om = await get_openmetadata_client(db)
        return await om.list_databases(limit)
    except RuntimeError as e:
        raise RuntimeError(f"OpenMetadata not configured: {e}")


async def list_tables(db: AsyncSession, database_fqn: str | None = None, limit: int = 100) -> list[dict]:
    """List tables, optionally filtered by database."""
    try:
        om = await get_openmetadata_client(db)
        return await om.list_tables(database_fqn, limit)
    except RuntimeError as e:
        raise RuntimeError(f"OpenMetadata not configured: {e}")


async def get_table(db: AsyncSession, table_fqn: str) -> dict:
    """Get table details including columns, schema, tags."""
    try:
        om = await get_openmetadata_client(db)
        return await om.get_table(table_fqn)
    except RuntimeError as e:
        raise RuntimeError(f"OpenMetadata not configured: {e}")


async def get_lineage(db: AsyncSession, entity_fqn: str, entity_type: str = "table") -> dict:
    """Get upstream/downstream lineage for an entity."""
    try:
        om = await get_openmetadata_client(db)
        return await om.get_lineage(entity_fqn, entity_type)
    except RuntimeError as e:
        raise RuntimeError(f"OpenMetadata not configured: {e}")


async def search(db: AsyncSession, query: str, limit: int = 20) -> list[dict]:
    """Search across all data assets."""
    try:
        om = await get_openmetadata_client(db)
        return await om.search(query, limit)
    except RuntimeError as e:
        raise RuntimeError(f"OpenMetadata not configured: {e}")


async def health_check(db: AsyncSession) -> bool:
    """Check OpenMetadata connectivity."""
    try:
        om = await get_openmetadata_client(db)
        return await om.health_check()
    except RuntimeError:
        return False
