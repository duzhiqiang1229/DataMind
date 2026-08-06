"""System service: configs + operation logs."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SystemConfig, OperationLog


async def list_configs(db: AsyncSession) -> list[dict]:
    result = await db.execute(select(SystemConfig).order_by(SystemConfig.config_key))
    configs = result.scalars().all()
    return [
        {
            "config_key": c.config_key,
            "config_value": c.config_value,
            "config_type": c.config_type,
            "description": c.description,
            "is_editable": c.is_editable,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in configs
    ]


async def update_config(
    db: AsyncSession, config_key: str, config_value: str, user_id: uuid.UUID
) -> dict | None:
    result = await db.execute(select(SystemConfig).where(SystemConfig.config_key == config_key))
    cfg = result.scalar_one_or_none()
    if not cfg:
        return None
    if not cfg.is_editable:
        raise ValueError("Config is not editable")
    cfg.config_value = config_value
    cfg.updated_by = user_id
    await db.commit()
    await db.refresh(cfg)
    return {
        "config_key": cfg.config_key,
        "config_value": cfg.config_value,
        "config_type": cfg.config_type,
        "description": cfg.description,
        "updated_at": cfg.updated_at.isoformat() if cfg.updated_at else None,
    }


async def list_logs(
    db: AsyncSession, page: int, page_size: int,
    module: Optional[str] = None, user_id: Optional[str] = None,
) -> tuple[list[dict], int]:
    query = select(OperationLog)
    count_q = select(func.count(OperationLog.id))

    if module:
        query = query.where(OperationLog.module == module)
        count_q = count_q.where(OperationLog.module == module)
    if user_id:
        uid = uuid.UUID(user_id)
        query = query.where(OperationLog.user_id == uid)
        count_q = count_q.where(OperationLog.user_id == uid)

    total = (await db.execute(count_q)).scalar_one()
    result = await db.execute(
        query.order_by(OperationLog.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    logs = result.scalars().all()
    return [
        {
            "id": str(l.id),
            "user_id": str(l.user_id) if l.user_id else None,
            "username": l.username,
            "module": l.module,
            "action": l.action,
            "target_type": l.target_type,
            "target_id": l.target_id,
            "description": l.description,
            "request_method": l.request_method,
            "request_path": l.request_path,
            "status_code": l.status_code,
            "ip_address": l.ip_address,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ], total


async def create_log(
    db: AsyncSession,
    user_id: Optional[uuid.UUID], username: Optional[str],
    module: str, action: str, description: str,
    target_type: Optional[str] = None, target_id: Optional[str] = None,
    request_method: Optional[str] = None, request_path: Optional[str] = None,
    request_body: Optional[str] = None, status_code: Optional[int] = None,
    ip_address: Optional[str] = None,
):
    log = OperationLog(
        user_id=user_id, username=username,
        module=module, action=action, description=description,
        target_type=target_type, target_id=target_id,
        request_method=request_method, request_path=request_path,
        request_body=request_body, status_code=status_code,
        ip_address=ip_address,
    )
    db.add(log)
    await db.commit()
