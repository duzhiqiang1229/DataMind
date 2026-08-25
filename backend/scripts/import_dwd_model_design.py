"""将当前 Doris DWD 物理表幂等同步为 DataMind 模型设计。"""

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
        "table": "dwd_fee_fees_df",
        "name": "应收费用明细事实",
        "domain": "收费域",
        "process": "应收费用管理",
        "grain": "每个应收费用ID（fees_id）一条记录",
        "description": "以应收费用为粒度，关联小区、房间、客户、收费项目、收费标准和车位维度的明细事实模型。",
        "sources": [
            "ods.ods_erp_tb_hspr_fees_f_d", "dim.dim_community", "dim.dim_room",
            "dim.dim_customer", "dim.dim_costitem", "dim.dim_coststandard", "dim.dim_parking",
        ],
    },
    {
        "table": "dwd_fee_feesdetail_df",
        "name": "实收费用明细事实",
        "domain": "收费域",
        "process": "收款管理",
        "grain": "每个实收明细ID（recd_id）一条记录",
        "description": "以实收明细为粒度，保留有效收款记录并补充物业、客户和收费项目维度属性。",
        "sources": [
            "ods.ods_erp_tb_hspr_feesdetail_f_d", "dim.dim_community", "dim.dim_room",
            "dim.dim_customer", "dim.dim_costitem",
        ],
    },
    {
        "table": "dwd_fee_precostsdetail_df",
        "name": "预交费用明细事实",
        "domain": "收费域",
        "process": "预交与冲抵",
        "grain": "每个预交明细ID（recd_id）一条记录",
        "description": "以预交明细为粒度，区分预存、预交及对应退款类型，并补充公共维度属性。",
        "sources": [
            "ods.ods_erp_tb_hspr_precostsdetail_f_d", "dim.dim_community", "dim.dim_room",
            "dim.dim_customer", "dim.dim_costitem",
        ],
    },
    {
        "table": "dwd_fee_offsetpredetail_df",
        "name": "预交冲抵明细事实",
        "domain": "收费域",
        "process": "预交与冲抵",
        "grain": "每个冲抵明细ID（iid）一条记录",
        "description": "以预交冲抵明细为粒度，区分预存冲抵和预收冲抵，并补充公共维度属性。",
        "sources": [
            "ods.ods_erp_tb_hspr_offsetpredetail_f_d", "dim.dim_community", "dim.dim_room",
            "dim.dim_customer", "dim.dim_costitem",
        ],
    },
    {
        "table": "dwd_fee_refundfees_df",
        "name": "退款费用明细事实",
        "domain": "收费域",
        "process": "退款管理",
        "grain": "每个退款ID（refund_id）一条记录",
        "description": "以退款业务为粒度，统一现金退款、预交退款、退款总额及带方向金额。",
        "sources": [
            "ods.ods_erp_tb_hspr_refundfees_f_d", "dim.dim_community", "dim.dim_room",
            "dim.dim_customer", "dim.dim_costitem",
        ],
    },
    {
        "table": "dwd_incident_accept_df",
        "name": "报事受理处理明细事实",
        "domain": "客户服务域",
        "process": "报事受理与处理",
        "grain": "每个报事ID（incident_id）一条累积快照记录",
        "description": "以报事为粒度，记录受理、派工、处理和完结过程及各阶段耗时。",
        "sources": [
            "ods.ods_erp_tb_hspr_incidentaccept_f_d", "dim.dim_community", "dim.dim_room",
            "dim.dim_customer", "dim.dim_incidenttype",
        ],
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
        cursor.execute(f"SHOW FULL COLUMNS FROM dwd.`{table}`")
        columns = cursor.fetchall()
        cursor.execute(f"SHOW CREATE TABLE dwd.`{table}`")
        ddl_row = cursor.fetchone()

    fields = []
    for index, column in enumerate(columns):
        fields.append({
            "field_name": column["Field"],
            "field_type": normalize_type(column["Type"]),
            "field_comment": (column.get("Comment") or None),
            "is_primary_key": str(column.get("Key", "")).upper() in {"YES", "PRI"},
            "is_partition": False,
            "default_value": None,
            "sort_order": index,
        })
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
                fqn = f"数据仓库.数据仓库.dwd.{spec['table']}"
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
                        layer="dwd",
                        database="dwd",
                        table_name=spec["table"],
                    )
                    session.add(model)
                    await session.flush()

                old_snapshot = [] if created else [
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
                fields_changed = old_snapshot != fields

                model.model_name = spec["name"]
                model.layer = "dwd"
                model.database = "dwd"
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
                        change_log="从当前 Doris DWD 物理表同步模型设计" if created else "同步 Doris 字段变更",
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
