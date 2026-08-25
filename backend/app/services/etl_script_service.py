"""SQL development script CRUD and datasource execution."""
import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EtlScript
from app.schemas.etl_script import EtlScriptCreate, EtlScriptUpdate


async def list_scripts(
    db: AsyncSession, page: int, page_size: int,
    language: Optional[str] = None, keyword: Optional[str] = None,
) -> tuple[list[dict], int]:
    query = select(EtlScript).where(EtlScript.language == "sql")
    count_q = select(func.count(EtlScript.id)).where(EtlScript.language == "sql")
    if language:
        query = query.where(EtlScript.language == language)
        count_q = count_q.where(EtlScript.language == language)
    if keyword:
        kw = f"%{keyword}%"
        query = query.where(EtlScript.script_name.ilike(kw))
        count_q = count_q.where(EtlScript.script_name.ilike(kw))
    total = (await db.execute(count_q)).scalar_one()
    result = await db.execute(
        query.order_by(EtlScript.updated_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    return [_to_dict(script) for script in result.scalars().all()], total


async def get_script(db: AsyncSession, script_id: uuid.UUID) -> dict | None:
    result = await db.execute(
        select(EtlScript).where(EtlScript.id == script_id, EtlScript.language == "sql")
    )
    script = result.scalar_one_or_none()
    return _to_dict(script) if script else None


async def create_script(
    db: AsyncSession, req: EtlScriptCreate, user_id: uuid.UUID,
) -> dict:
    script = EtlScript(
        script_name=req.script_name,
        script_code=req.script_code or f"etl_sql_{uuid.uuid4().hex[:8]}",
        language="sql",
        content=req.content,
        description=req.description,
        created_by=user_id,
    )
    db.add(script)
    await db.commit()
    await db.refresh(script)
    return _to_dict(script)


async def update_script(
    db: AsyncSession, script_id: uuid.UUID, req: EtlScriptUpdate,
) -> dict | None:
    result = await db.execute(
        select(EtlScript).where(EtlScript.id == script_id, EtlScript.language == "sql")
    )
    script = result.scalar_one_or_none()
    if not script:
        return None
    if req.script_name is not None:
        script.script_name = req.script_name
    if req.content is not None:
        script.content = req.content
    if req.description is not None:
        script.description = req.description
    await db.commit()
    await db.refresh(script)
    return _to_dict(script)


async def delete_script(db: AsyncSession, script_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(EtlScript).where(EtlScript.id == script_id, EtlScript.language == "sql")
    )
    script = result.scalar_one_or_none()
    if not script:
        return False
    await db.delete(script)
    await db.commit()
    return True


async def execute_script(
    db: AsyncSession,
    script_id: uuid.UUID,
    datasource_id: Optional[str],
    database: Optional[str],
    limit: int,
) -> dict:
    result = await db.execute(
        select(EtlScript).where(EtlScript.id == script_id, EtlScript.language == "sql")
    )
    script = result.scalar_one_or_none()
    if not script:
        raise ValueError("SQL 脚本不存在")
    if not datasource_id:
        raise ValueError("SQL 执行需要选择数据源")

    from app.services.datasource_service import execute_query

    return await execute_query(
        db, uuid.UUID(datasource_id), script.content, limit, database=database,
    )


def _to_dict(script: EtlScript) -> dict:
    return {
        "id": str(script.id),
        "script_name": script.script_name,
        "script_code": script.script_code,
        "language": script.language,
        "content": script.content,
        "description": script.description,
        "created_at": script.created_at.isoformat() if script.created_at else None,
        "updated_at": script.updated_at.isoformat() if script.updated_at else None,
    }
