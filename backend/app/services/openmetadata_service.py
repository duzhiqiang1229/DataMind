"""OpenMetadata-backed catalog, governance, quality, and lineage service."""

import asyncio
from collections.abc import Awaitable
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.component_service import get_openmetadata_client


async def _run(db: AsyncSession, operation: str, call: Awaitable[Any]) -> Any:
    try:
        return await call
    except RuntimeError as exc:
        raise RuntimeError(f"OpenMetadata 未配置或不可用：{exc}") from exc
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        raise RuntimeError(f"OpenMetadata {operation}失败（HTTP {status}）") from exc
    except httpx.RequestError as exc:
        raise RuntimeError(f"无法连接 OpenMetadata：{exc}") from exc


async def _client(db: AsyncSession):
    try:
        return await get_openmetadata_client(db)
    except RuntimeError as exc:
        raise RuntimeError(f"OpenMetadata 未配置：{exc}") from exc


async def list_databases(db: AsyncSession, limit: int = 100) -> list[dict]:
    om = await _client(db)
    return await _run(db, "读取数据库", om.list_databases(limit))


async def list_tables(db: AsyncSession, database_fqn: str | None = None, limit: int = 100) -> list[dict]:
    om = await _client(db)
    return await _run(db, "读取数据表", om.list_tables(database_fqn, limit))


async def get_table(db: AsyncSession, table_fqn: str) -> dict:
    om = await _client(db)
    table, quality = await _run(
        db,
        "读取表详情",
        asyncio.gather(om.get_table(table_fqn), om.list_test_cases(table_fqn)),
    )
    table["quality"] = quality
    return table


async def get_lineage(db: AsyncSession, entity_fqn: str, entity_type: str = "table") -> dict:
    om = await _client(db)
    return await _run(db, "读取血缘", om.get_lineage(entity_fqn, entity_type))


async def search(db: AsyncSession, query: str, limit: int = 20) -> list[dict]:
    om = await _client(db)
    return await _run(db, "搜索资产", om.search(query, limit))


async def search_assets(
    db: AsyncSession,
    query: str,
    entity_type: str,
    page: int,
    page_size: int,
) -> dict:
    om = await _client(db)
    return await _run(
        db,
        "搜索资产",
        om.search_assets(query, entity_type, (page - 1) * page_size, page_size),
    )


async def summary(db: AsyncSession) -> dict:
    om = await _client(db)
    return await _run(db, "汇总资产", om.summary())


async def governance(db: AsyncSession, limit: int = 100) -> dict:
    om = await _client(db)
    return await _run(db, "读取治理信息", om.governance(limit))


async def quality(db: AsyncSession, table_fqn: str | None = None, limit: int = 100) -> dict:
    om = await _client(db)
    return await _run(db, "读取质量检查", om.list_test_cases(table_fqn, limit))


async def health_check(db: AsyncSession) -> bool:
    try:
        om = await get_openmetadata_client(db)
        return await om.health_check()
    except Exception:
        return False
