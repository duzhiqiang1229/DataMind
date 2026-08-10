"""Data model service: CRUD + fields + versions + DDL generation."""
import uuid
from typing import Optional

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger

from app.models import DataModel, DataModelField, DataModelVersion
from app.schemas.data_model import DataModelCreate, DataModelUpdate, DataModelFieldItem


async def list_models(
    db: AsyncSession, page: int, page_size: int,
    layer: Optional[str] = None, status: Optional[str] = None,
    business_domain: Optional[str] = None, data_domain: Optional[str] = None,
) -> tuple[list[dict], int]:
    query = select(DataModel).options(selectinload(DataModel.fields))
    count_q = select(func.count(DataModel.id))
    if layer:
        query = query.where(DataModel.layer == layer)
        count_q = count_q.where(DataModel.layer == layer)
    if status:
        query = query.where(DataModel.status == status)
        count_q = count_q.where(DataModel.status == status)
    if business_domain:
        query = query.where(DataModel.business_domain == business_domain)
        count_q = count_q.where(DataModel.business_domain == business_domain)
    if data_domain:
        query = query.where(DataModel.data_domain == data_domain)
        count_q = count_q.where(DataModel.data_domain == data_domain)

    total = (await db.execute(count_q)).scalar_one()
    result = await db.execute(
        query.order_by(DataModel.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    models = result.scalars().all()
    return [_to_dict(m) for m in models], total


async def get_model(db: AsyncSession, model_id: uuid.UUID) -> dict | None:
    result = await db.execute(
        select(DataModel)
        .options(selectinload(DataModel.fields), selectinload(DataModel.versions))
        .where(DataModel.id == model_id)
    )
    m = result.scalar_one_or_none()
    if not m:
        return None
    return _to_dict(m, include_versions=True)


async def create_model(
    db: AsyncSession, req: DataModelCreate, user_id: uuid.UUID
) -> dict:
    # Auto-generate a unique model code if not provided
    model_code = req.model_code or f"{req.layer}_{req.table_name}"
    existing = await db.execute(
        select(DataModel.id).where(DataModel.model_code == model_code)
    )
    if existing.scalar_one_or_none():
        model_code = f"{model_code}_{uuid.uuid4().hex[:4]}"

    model = DataModel(
        model_name=req.model_name,
        model_code=model_code,
        layer=req.layer,
        database=req.database,
        table_name=req.table_name,
        description=req.description,
        etl_sql=req.etl_sql,
        business_domain=req.business_domain,
        data_domain=req.data_domain,
        current_version=1,
        status="draft",
        created_by=user_id,
    )
    db.add(model)
    await db.flush()

    for f in req.fields:
        db.add(DataModelField(
            model_id=model.id,
            field_name=f.field_name,
            field_type=f.field_type,
            field_comment=f.field_comment,
            is_primary_key=f.is_primary_key,
            is_partition=f.is_partition,
            default_value=f.default_value,
            sort_order=f.sort_order,
        ))

    # generate initial version with DDL
    ddl = _generate_ddl(model, req.fields)
    db.add(DataModelVersion(
        model_id=model.id,
        version=1,
        table_ddl=ddl,
        field_snapshot=[f.model_dump() for f in req.fields],
        change_log="Initial version",
        created_by=user_id,
    ))

    await db.commit()
    await db.refresh(model)
    return await get_model(db, model.id)


async def update_model(
    db: AsyncSession, model_id: uuid.UUID, req: DataModelUpdate
) -> dict | None:
    result = await db.execute(
        select(DataModel).options(selectinload(DataModel.fields)).where(DataModel.id == model_id)
    )
    model = result.scalar_one_or_none()
    if not model:
        return None

    if req.model_name is not None:
        model.model_name = req.model_name
    if req.description is not None:
        model.description = req.description
    if req.status is not None:
        model.status = req.status
    if req.etl_sql is not None:
        model.etl_sql = req.etl_sql
    if req.business_domain is not None:
        model.business_domain = req.business_domain
    if req.data_domain is not None:
        model.data_domain = req.data_domain

    # if fields changed, create a new version
    if req.fields is not None:
        # delete old fields
        await db.execute(delete(DataModelField).where(DataModelField.model_id == model_id))
        for f in req.fields:
            db.add(DataModelField(
                model_id=model_id,
                field_name=f.field_name,
                field_type=f.field_type,
                field_comment=f.field_comment,
                is_primary_key=f.is_primary_key,
                is_partition=f.is_partition,
                default_value=f.default_value,
                sort_order=f.sort_order,
            ))

        # create new version
        new_version = model.current_version + 1
        ddl = _generate_ddl(model, req.fields)
        db.add(DataModelVersion(
            model_id=model_id,
            version=new_version,
            table_ddl=ddl,
            field_snapshot=[f.model_dump() for f in req.fields],
            change_log=req.description or f"Version {new_version}",
        ))
        model.current_version = new_version

    await db.commit()
    await db.refresh(model)
    return await get_model(db, model_id)


async def delete_model(db: AsyncSession, model_id: uuid.UUID) -> bool:
    result = await db.execute(select(DataModel).where(DataModel.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        return False
    # Drop the physical table in Doris first
    await _execute_on_doris(
        db,
        f"DROP TABLE IF EXISTS {model.database}.{model.table_name}"
    )
    await db.delete(model)
    await db.commit()
    return True


async def publish_model(db: AsyncSession, model_id: uuid.UUID) -> dict | None:
    """Publish a model: generate Doris DDL and execute it to create the table."""
    result = await db.execute(
        select(DataModel)
        .options(selectinload(DataModel.fields))
        .where(DataModel.id == model_id)
    )
    model = result.scalar_one_or_none()
    if not model:
        return None
    if not model.fields:
        raise ValueError("模型没有字段，无法生成建表语句")

    field_items = [
        DataModelFieldItem(
            field_name=f.field_name,
            field_type=f.field_type,
            field_comment=f.field_comment,
            is_primary_key=f.is_primary_key,
            is_partition=f.is_partition,
            default_value=f.default_value,
            sort_order=f.sort_order,
        )
        for f in sorted(model.fields, key=lambda x: x.sort_order)
    ]
    ddl = _generate_ddl(model, field_items)

    await _execute_on_doris(db, ddl)

    model.status = "active"
    await db.commit()
    await db.refresh(model)
    return await get_model(db, model_id)


async def _execute_on_doris(db: AsyncSession, sql: str) -> None:
    """Execute SQL on the Doris data source from data source management.

    The Doris component config is no longer used; Doris is managed as a
    regular data source (source_type='doris') in the data source module.
    """
    import pymysql

    from app.core.security import decrypt_value
    from app.models import DataSource

    result = await db.execute(
        select(DataSource).where(
            DataSource.source_type == "doris",
            DataSource.status == "active",
        )
    )
    ds = result.scalars().first()
    if not ds:
        raise ValueError("未配置 Doris 数据源，请在数据源管理中配置")

    password = decrypt_value(ds.password_encrypted)
    conn = pymysql.connect(
        host=ds.host, port=ds.port, user=ds.username, password=password,
        charset="utf8mb4", connect_timeout=10, read_timeout=300,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    finally:
        conn.close()


async def list_versions(
    db: AsyncSession, model_id: uuid.UUID
) -> list[dict]:
    result = await db.execute(
        select(DataModelVersion)
        .where(DataModelVersion.model_id == model_id)
        .order_by(DataModelVersion.version.desc())
    )
    versions = result.scalars().all()
    return [
        {
            "id": str(v.id),
            "model_id": str(v.model_id),
            "version": v.version,
            "table_ddl": v.table_ddl,
            "change_log": v.change_log,
            "created_by": str(v.created_by) if v.created_by else None,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in versions
    ]


def _generate_ddl(model: DataModel, fields: list[DataModelFieldItem]) -> str:
    """Generate CREATE TABLE DDL from model fields (Doris dialect)."""
    col_defs = []
    for f in fields:
        parts = [f.field_name, f.field_type]
        if f.is_primary_key:
            parts.append("KEY")
        if f.default_value:
            parts.append(f"DEFAULT '{f.default_value}'")
        col_defs.append("  " + " ".join(parts))

    partition_clause = ""
    partition_fields = [f for f in fields if f.is_partition]
    if partition_fields:
        partition_clause = f"\nPARTITION BY ({', '.join(f.field_name for f in partition_fields)})"

    pk_fields = [f for f in fields if f.is_primary_key]
    distributed_key = ", ".join(f.field_name for f in pk_fields) or "id"
    ddl = (
        f"CREATE TABLE IF NOT EXISTS {model.database}.{model.table_name} (\n"
        + ",\n".join(col_defs)
        + "\n)\nDISTRIBUTED BY HASH("
        + distributed_key
        + ") BUCKETS 10"
        + partition_clause
        + "\nPROPERTIES (\n  'replication_num' = '1'\n);"
    )
    return ddl


def _to_dict(m: DataModel, include_versions: bool = False) -> dict:
    d = {
        "id": str(m.id),
        "model_name": m.model_name,
        "model_code": m.model_code,
        "layer": m.layer,
        "database": m.database,
        "table_name": m.table_name,
        "description": m.description,
        "etl_sql": m.etl_sql,
        "business_domain": m.business_domain,
        "data_domain": m.data_domain,
        "status": m.status,
        "current_version": m.current_version,
        "fields": [
            {
                "id": str(f.id),
                "field_name": f.field_name,
                "field_type": f.field_type,
                "field_comment": f.field_comment,
                "is_primary_key": f.is_primary_key,
                "is_partition": f.is_partition,
                "default_value": f.default_value,
                "sort_order": f.sort_order,
            }
            for f in (m.fields or [])
        ],
        "created_by": str(m.created_by) if m.created_by else None,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "updated_at": m.updated_at.isoformat() if m.updated_at else None,
    }
    if include_versions:
        d["versions"] = [
            {
                "id": str(v.id),
                "version": v.version,
                "change_log": v.change_log,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in (m.versions or [])
        ]
    return d
