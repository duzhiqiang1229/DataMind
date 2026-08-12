"""Import the current OpenMetadata warehouse snapshot into DataMind modeling.

The import is idempotent. It replaces only the original demo catalog records,
backs up the existing modeling configuration, and marks imported models as
external so deleting a design record can never drop an existing Doris table.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.core.database import async_session
from app.models import (
    BusinessDomain,
    DataDomain,
    DataModel,
    DataModelField,
    DataModelVersion,
)


DATA_DOMAINS = [
    ("common", "公共维度域", "跨主题共享的日期、行政区划和公共维度", 10),
    ("property_asset", "物业资产域", "小区、楼栋、房间、车位等空间资产", 20),
    ("customer_lifecycle", "客户入住域", "客户、入住关系和房态变化", 30),
    ("fee_finance", "收费财务域", "应收、实收、预收、冲抵、退款和现金流", 40),
    ("inspection", "品质巡检域", "巡检计划、任务、点位和异常", 50),
    ("incident", "客户事件域", "事件受理、处理和回复", 60),
    ("charging", "充电运营域", "充电订单、用户、设备和端口状态", 70),
]

BUSINESS_PROCESSES = [
    ("common_dimension", "公共维度维护", "公共维度域", "维护跨主题复用的日期和区域维度", 10),
    ("property_resource", "物业资源维护", "物业资产域", "维护小区、楼栋、房间和车位主数据", 20),
    ("customer_profile", "客户档案维护", "客户入住域", "维护客户主数据", 30),
    ("customer_residency", "客户入住管理", "客户入住域", "记录客户入住关系和历史变化", 40),
    ("occupancy_snapshot", "房态统计", "客户入住域", "按日统计入住与空置状态", 50),
    ("fee_receivable", "费用应收", "收费财务域", "生成和管理应收费用", 60),
    ("fee_collection", "费用实收", "收费财务域", "记录收款和实收明细", 70),
    ("fee_prepayment", "预收与冲抵", "收费财务域", "管理预收款及其冲抵过程", 80),
    ("fee_refund", "费用退款", "收费财务域", "记录退费业务", 90),
    ("cash_flow", "现金流汇总", "收费财务域", "形成收费现金流日报", 100),
    ("inspection_plan", "巡检计划", "品质巡检域", "定义巡检计划和巡检等级", 110),
    ("inspection_execution", "巡检执行", "品质巡检域", "记录巡检任务、点位和异常", 120),
    ("incident_accept", "事件受理", "客户事件域", "记录客户事件受理", 130),
    ("incident_reply", "事件回复", "客户事件域", "记录事件处理结果和回复", 140),
    ("charging_order", "充电订单", "充电运营域", "记录充电及充值订单", 150),
    ("charging_device", "充电设备监控", "充电运营域", "监控设备和端口运行状态", 160),
]

MODEL_NAMES = {
    "ads_cash_flow_daily_report_df": "现金流日报应用模型",
    "dim_charge_mode": "收费方式维度",
    "dim_community": "小区维度",
    "dim_cost_item": "收费项目维度",
    "dim_cost_standard": "收费标准维度",
    "dim_customer": "客户维度",
    "dim_customer_live_scd": "客户入住关系历史维度",
    "dim_date": "日期维度",
    "dim_fee": "费用维度",
    "dim_incident_type": "事件类型维度",
    "dim_inspection_level": "巡检等级维度",
    "dim_inspection_plan": "巡检计划维度",
    "dim_parking": "车位维度",
    "dim_pub_districtname_f_d": "行政区划维度",
    "dim_room": "房间维度",
    "dwd_cp_task_df": "巡检任务明细事实",
    "dwd_cp_taskpoint_df": "巡检点位明细事实",
    "dwd_fee_fees_df": "应收费用明细事实",
    "dwd_fee_feesdetail_df": "实收费用明细事实",
    "dwd_fee_offsetpredetail_df": "预收冲抵明细事实",
    "dwd_fee_precosts_df": "预收费用明细事实",
    "dwd_fee_precostsdetail_df": "预收费用项目明细事实",
    "dwd_fee_refundfees_df": "退款费用明细事实",
    "dwd_incident_accept_df": "事件受理明细事实",
    "dwd_incident_reply_df": "事件回复明细事实",
    "dws_cp_point_daily_df": "巡检点位日汇总",
    "dws_cp_task_daily_df": "巡检任务日汇总",
    "dws_fee_arrears_daily_df": "欠费日汇总",
    "dws_fee_received_arrears_daily_df": "实收欠费日汇总",
    "dws_fee_received_daily_df": "实收费用日汇总",
    "dws_fee_refund_daily_df": "退款日汇总",
    "dws_incident_reply_daily_df": "事件回复日汇总",
    "dws_incident_summary_daily_df": "事件受理日汇总",
    "dws_occupancy_daily_df": "入住与房态日汇总",
}

DEMO_DOMAIN_CODES = {"user", "order", "product", "payment", "inventory", "marketing", "finance", "log"}
DEMO_PROCESS_CODES = {"hr", "supply_chain", "customer", "manufacturing", "marketing", "finance", "sales", "risk"}


def classify(name: str) -> tuple[str, str]:
    lower = name.lower()
    if "cash_flow" in lower:
        return "收费财务域", "现金流汇总"
    if "cdzapi" in lower:
        process = "充电设备监控" if any(key in lower for key in ("dev", "port")) else "充电订单"
        return "充电运营域", process
    if any(key in lower for key in ("incident", "corpincident")):
        return "客户事件域", "事件回复" if "reply" in lower else "事件受理"
    if any(key in lower for key in ("cp_", "inspection", "taskpoint")):
        return "品质巡检域", "巡检计划" if any(key in lower for key in ("plan", "level")) else "巡检执行"
    if any(key in lower for key in ("feesdetail", "received")):
        return "收费财务域", "费用实收"
    if any(key in lower for key in ("offsetpre", "precost")):
        return "收费财务域", "预收与冲抵"
    if "refund" in lower:
        return "收费财务域", "费用退款"
    if any(key in lower for key in ("fee", "costitem", "coststandard", "chargemode", "cost_item", "cost_standard", "charge_mode")):
        return "收费财务域", "费用应收"
    if any(key in lower for key in ("customerlive", "customer_live", "occupancy")):
        return "客户入住域", "房态统计" if "occupancy" in lower else "客户入住管理"
    if "customer" in lower:
        return "客户入住域", "客户档案维护"
    if any(key in lower for key in ("community", "building", "room", "parking")):
        return "物业资产域", "物业资源维护"
    return "公共维度域", "公共维度维护"


def title_for(name: str) -> str:
    if name in MODEL_NAMES:
        return MODEL_NAMES[name]
    source_titles = {
        "cdorders": "充电订单源表",
        "chargeorderweekstatistics": "充电订单周统计源表",
        "czorders": "充值订单源表",
        "devportreal": "充电端口实时状态源表",
        "dev": "充电设备源表",
        "users": "充电用户源表",
        "cp_plan": "巡检计划源表",
        "cp_tasklevel": "巡检等级源表",
        "cp_taskpointincident": "巡检点位异常源表",
        "cp_taskpoint": "巡检点位源表",
        "cp_task": "巡检任务源表",
        "chargemode": "收费方式源表",
        "building": "楼栋源表",
        "corpincidenttype": "事件类型源表",
        "costitem": "收费项目源表",
        "coststandard": "收费标准源表",
        "customerlive": "客户入住关系源表",
        "customer": "客户源表",
        "feesdetail": "实收费用源表",
        "fees": "应收费用源表",
        "incidentaccept": "事件受理源表",
        "incidentreply": "事件回复源表",
        "offsetpredetail": "预收冲抵源表",
        "parking": "车位源表",
        "precostsdetail": "预收费用项目源表",
        "precosts": "预收费用源表",
        "refundfees": "退款费用源表",
        "room": "房间源表",
    }
    normalized = name.lower()
    for key in sorted(source_titles, key=len, reverse=True):
        if key in normalized:
            return source_titles[key]
    return name


def grain_for(name: str, layer: str) -> str:
    if layer == "ods":
        return "源系统业务记录粒度，按采集批次保留"
    if layer == "dim":
        return "每个业务主键一条当前维度记录" if "scd" not in name else "每个业务主键在每个有效期一条历史记录"
    if layer == "dwd":
        return "每个业务明细事件一条记录"
    if layer == "dws":
        return "每日、按核心业务维度汇总一条记录"
    return "每日、按项目与收费日期汇总一条现金流记录"


def strategy_for(name: str, layer: str) -> str:
    if name == "dim_customer_live_scd":
        return "scd2"
    if name == "dim_date":
        return "static"
    if layer == "ods":
        return "incremental" if name.endswith("_i_d") else "full_snapshot"
    if layer == "dim":
        return "full_merge"
    return "partition_overwrite"


def valid_comment(value: str | None) -> str | None:
    if not value or "�" in value:
        return None
    return value[:200]


def build_sources(analysis: dict) -> dict[str, list[str]]:
    sources: dict[str, list[str]] = {}
    for job in analysis.get("jobLineage", []):
        for output in job.get("output_tables", []):
            sources[output] = job.get("input_tables", [])
    sources.update({
        "dim_charge_mode": ["ods_erp_tb_dictionary_chargemode_f_d"],
        "dim_inspection_level": ["ods_erp_tb_cp_tasklevel_f_d"],
        "dwd_fee_feesdetail_df": ["ods_erp_tb_hspr_feesdetail_f_d", "dim_community", "dim_customer", "dim_room", "dim_cost_item", "dim_fee"],
        "dwd_fee_offsetpredetail_df": ["ods_erp_tb_hspr_offsetpredetail_f_d", "dim_community", "dim_customer", "dim_room", "dim_cost_item", "dim_fee"],
    })
    return sources


async def backup_current(session, path: Path) -> None:
    models = (
        await session.execute(
            select(DataModel)
            .options(selectinload(DataModel.fields), selectinload(DataModel.versions))
            .order_by(DataModel.created_at)
        )
    ).scalars().all()
    domains = (await session.execute(select(DataDomain).order_by(DataDomain.sort_order))).scalars().all()
    processes = (await session.execute(select(BusinessDomain).order_by(BusinessDomain.sort_order))).scalars().all()
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "dataDomains": [
            {"domain_code": d.domain_code, "domain_name": d.domain_name, "description": d.description, "sort_order": d.sort_order}
            for d in domains
        ],
        "businessProcesses": [
            {"domain_code": d.domain_code, "domain_name": d.domain_name, "data_domain": d.data_domain, "description": d.description, "sort_order": d.sort_order}
            for d in processes
        ],
        "models": [
            {
                "model_code": m.model_code,
                "model_name": m.model_name,
                "layer": m.layer,
                "database": m.database,
                "table_name": m.table_name,
                "description": m.description,
                "business_domain": m.business_domain,
                "data_domain": m.data_domain,
                "status": m.status,
                "fields": [
                    {"field_name": f.field_name, "field_type": f.field_type, "field_comment": f.field_comment}
                    for f in m.fields
                ],
            }
            for m in models
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


async def run(snapshot_path: Path, analysis_path: Path, backup_path: Path) -> None:
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    source_map = build_sources(analysis)

    async with async_session() as session:
        await backup_current(session, backup_path)

        # Remove only the known bootstrap demo records, never user-created data.
        await session.execute(delete(DataModel).where(DataModel.model_code == "ods_test_dm_order"))
        await session.execute(delete(DataDomain).where(DataDomain.domain_code.in_(DEMO_DOMAIN_CODES)))
        await session.execute(delete(BusinessDomain).where(BusinessDomain.domain_code.in_(DEMO_PROCESS_CODES)))

        for code, name, description, order in DATA_DOMAINS:
            item = (await session.execute(select(DataDomain).where(DataDomain.domain_code == code))).scalar_one_or_none()
            if item is None:
                item = DataDomain(domain_code=code, domain_name=name, description=description, sort_order=order)
                session.add(item)
            else:
                item.domain_name, item.description, item.sort_order = name, description, order

        for code, name, data_domain, description, order in BUSINESS_PROCESSES:
            item = (await session.execute(select(BusinessDomain).where(BusinessDomain.domain_code == code))).scalar_one_or_none()
            if item is None:
                item = BusinessDomain(
                    domain_code=code,
                    domain_name=name,
                    data_domain=data_domain,
                    description=description,
                    sort_order=order,
                )
                session.add(item)
            else:
                item.domain_name, item.data_domain = name, data_domain
                item.description, item.sort_order = description, order

        await session.flush()

        imported = 0
        for table in snapshot.get("warehouseTables", []):
            fqn = table.get("fullyQualifiedName") or ""
            parts = fqn.split(".")
            layer = parts[-2].lower() if len(parts) >= 2 else ""
            if layer not in {"ods", "dim", "dwd", "dws", "ads"}:
                continue
            name = table["name"]
            model_code = f"warehouse_{name}"
            model = (
                await session.execute(
                    select(DataModel).options(selectinload(DataModel.fields)).where(DataModel.model_code == model_code)
                )
            ).scalar_one_or_none()
            domain, process = classify(name)
            if model is None:
                model = DataModel(model_code=model_code, model_name=title_for(name), layer=layer, database=layer, table_name=name)
                session.add(model)
                await session.flush()
            model.model_name = title_for(name)
            model.layer = layer
            model.database = layer
            model.table_name = name
            model.description = f"从 OpenMetadata 同步的现有 {layer.upper()} 物理表"
            model.data_domain = domain
            model.business_domain = process
            model.model_grain = grain_for(name, layer)
            model.update_strategy = strategy_for(name, layer)
            model.source_tables = source_map.get(name, [])
            model.source_fqn = fqn
            model.is_external = True
            model.status = "active"
            model.current_version = 1

            await session.execute(delete(DataModelField).where(DataModelField.model_id == model.id))
            partition_columns = {
                column.get("columnName")
                for column in (table.get("tablePartition") or {}).get("columns", [])
            }
            for index, column in enumerate(table.get("columns") or []):
                constraint = (column.get("constraint") or "").upper()
                session.add(DataModelField(
                    model_id=model.id,
                    field_name=column["name"][:100],
                    field_type=(column.get("dataTypeDisplay") or column.get("dataType") or "STRING")[:50].upper(),
                    field_comment=valid_comment(column.get("description")),
                    is_primary_key=constraint == "PRIMARY_KEY",
                    is_partition=column["name"] in partition_columns,
                    sort_order=index,
                ))
            imported += 1

        await session.commit()
        print(json.dumps({
            "data_domains": len(DATA_DOMAINS),
            "business_processes": len(BUSINESS_PROCESSES),
            "models": imported,
            "backup": str(backup_path),
        }, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--backup", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(run(args.snapshot, args.analysis, args.backup))


if __name__ == "__main__":
    main()
