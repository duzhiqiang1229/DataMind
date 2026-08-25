"""将当前 Doris DWS 物理表幂等同步为 DataMind 模型设计。"""

from __future__ import annotations

import asyncio
import json
import re

import pymysql
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import selectinload

from app.core.database import async_session
from app.core.security import decrypt_value
from app.models import DataModel, DataModelField, DataModelVersion, DataSource


MODELS = [
    {
        "table": "dws_fee_receivable_daily_df",
        "name": "应收费用日汇总",
        "domain": "收费域",
        "process": "应收费用管理",
        "grain": "应收日期、小区、楼栋、收费项目、物业用途、客户类型粒度",
        "description": "按日汇总各小区、楼栋和收费项目的应收金额及应收笔数。",
        "sources": ["dwd.dwd_fee_fees_df"],
    },
    {
        "table": "dws_fee_cashflow_daily_df",
        "name": "收费现金流日汇总",
        "domain": "收费域",
        "process": "收款管理",
        "grain": "交易日期、小区、楼栋、收费项目、资金类型、资金方向、收退款方式、物业用途、客户类型粒度",
        "description": "统一汇总实收、预交、预存及退款的流入、流出和净现金流。",
        "sources": [
            "dwd.dwd_fee_feesdetail_df",
            "dwd.dwd_fee_precostsdetail_df",
            "dwd.dwd_fee_refundfees_df",
        ],
    },
    {
        "table": "dws_fee_settlement_snapshot_df",
        "name": "应收费用核销汇总快照",
        "domain": "收费域",
        "process": "应收费用管理",
        "grain": "快照日期、应收日期、小区、楼栋、收费项目、物业用途、客户类型粒度",
        "description": "汇总应收、实收、预交、预存冲抵及各类退款，计算净核销、未核销和超收金额。",
        "sources": [
            "dwd.dwd_fee_fees_df",
            "dwd.dwd_fee_feesdetail_df",
            "dwd.dwd_fee_precostsdetail_df",
            "dwd.dwd_fee_offsetpredetail_df",
            "dwd.dwd_fee_refundfees_df",
        ],
    },
    {
        "table": "dws_incident_daily_df",
        "name": "报事处理日汇总",
        "domain": "客户服务域",
        "process": "报事受理与处理",
        "grain": "报事日期、小区、报事类型层级、报事方式粒度",
        "description": "按日汇总报事、派工、完结、未完结数量及派工和完结耗时。",
        "sources": ["dwd.dwd_incident_accept_df"],
    },
]


def normalize_type(value: str) -> str:
    value = value.upper()
    value = re.sub(r"^DECIMALV3", "DECIMAL", value)
    value = re.sub(r"^DATETIMEV2(?:\(0\))?$", "DATETIME", value)
    value = re.sub(r"^DATEV2$", "DATE", value)
    return value


def read_physical_table(conn, table: str) -> tuple[list[dict], str]:
    with conn.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute(f"SHOW FULL COLUMNS FROM dws.`{table}`")
        columns = cursor.fetchall()
        cursor.execute(f"SHOW CREATE TABLE dws.`{table}`")
        ddl_row = cursor.fetchone()

    fields = [
        {
            "field_name": column["Field"],
            "field_type": normalize_type(column["Type"]),
            "field_comment": column.get("Comment") or None,
            "is_primary_key": str(column.get("Key", "")).upper() in {"YES", "PRI"},
            "is_partition": False,
            "default_value": None,
            "sort_order": index,
        }
        for index, column in enumerate(columns)
    ]
    ddl = next((value for key, value in ddl_row.items() if "create table" in key.lower()), "")
    return fields, ddl


async def run() -> None:
    async with async_session() as session:
        source = (
            await session.execute(
                select(DataSource).where(
                    DataSource.source_type == "doris",
                    DataSource.status == "active",
                )
            )
        ).scalars().first()
        if source is None:
            raise RuntimeError("没有可用的 Doris 数据源")

        conn = pymysql.connect(
            host=source.host,
            port=source.port,
            user=source.username,
            password=decrypt_value(source.password_encrypted),
            charset="utf8mb4",
            connect_timeout=10,
            read_timeout=120,
        )
        results = []
        try:
            for spec in MODELS:
                fields, ddl = read_physical_table(conn, spec["table"])
                code = f"warehouse_{spec['table']}"
                fqn = f"数据仓库.数据仓库.dws.{spec['table']}"
                model = (
                    await session.execute(
                        select(DataModel)
                        .options(selectinload(DataModel.fields))
                        .where(or_(DataModel.model_code == code, DataModel.source_fqn == fqn))
                    )
                ).scalars().first()

                created = model is None
                if created:
                    model = DataModel(
                        model_code=code,
                        model_name=spec["name"],
                        layer="dws",
                        database="dws",
                        table_name=spec["table"],
                    )
                    session.add(model)
                    await session.flush()

                old_fields = [] if created else [
                    {
                        "field_name": item.field_name,
                        "field_type": item.field_type,
                        "field_comment": item.field_comment,
                        "is_primary_key": item.is_primary_key,
                        "is_partition": item.is_partition,
                        "default_value": item.default_value,
                        "sort_order": item.sort_order,
                    }
                    for item in sorted(model.fields, key=lambda value: value.sort_order)
                ]
                fields_changed = old_fields != fields

                model.model_name = spec["name"]
                model.layer = "dws"
                model.database = "dws"
                model.table_name = spec["table"]
                model.description = spec["description"]
                model.data_domain = spec["domain"]
                model.business_domain = spec["process"]
                model.model_grain = spec["grain"]
                model.update_strategy = "full_snapshot"
                model.source_tables = spec["sources"]
                model.source_fqn = fqn
                model.is_external = True
                model.status = "active"

                if created or fields_changed:
                    await session.execute(delete(DataModelField).where(DataModelField.model_id == model.id))
                    for item in fields:
                        session.add(DataModelField(model_id=model.id, **item))

                    version = 1 if created else model.current_version + 1
                    model.current_version = version
                    session.add(DataModelVersion(
                        model_id=model.id,
                        version=version,
                        table_ddl=ddl,
                        field_snapshot=fields,
                        change_log="从当前 Doris DWS 物理表同步模型设计" if created else "同步 Doris 字段变更",
                    ))

                results.append({
                    "table": spec["table"],
                    "model": spec["name"],
                    "fields": len(fields),
                    "created": created,
                    "version": model.current_version,
                })

            await session.commit()
        finally:
            conn.close()

        print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(run())
