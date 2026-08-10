"""DAG workflow service: CRUD + Airflow DAG file generation & deployment."""
import uuid
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DagDefinition, DagNode
from app.schemas.dag import DagDefinitionCreate, DagDefinitionUpdate


async def list_dags(
    db: AsyncSession, page: int, page_size: int,
) -> tuple[list[dict], int]:
    count_q = select(func.count(DagDefinition.id))
    total = (await db.execute(count_q)).scalar_one()
    result = await db.execute(
        select(DagDefinition)
        .order_by(DagDefinition.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    return [_to_dict(d) for d in result.scalars().all()], total


async def get_dag(db: AsyncSession, dag_id: uuid.UUID) -> dict | None:
    result = await db.execute(
        select(DagDefinition).where(DagDefinition.id == dag_id)
    )
    d = result.scalar_one_or_none()
    return _to_dict(d) if d else None


async def create_dag(
    db: AsyncSession, req: DagDefinitionCreate,
) -> dict:
    dag_id = f"datamind_wf_{uuid.uuid4().hex[:8]}"
    d = DagDefinition(
        dag_id=dag_id,
        dag_name=req.dag_name,
        schedule=req.schedule,
        description=req.description,
        status="draft",
    )
    db.add(d)
    await db.flush()
    _add_nodes(db, d.id, req.nodes)
    await db.commit()
    return await _reload(db, d.id)


async def update_dag(
    db: AsyncSession, dag_id: uuid.UUID, req: DagDefinitionUpdate,
) -> dict | None:
    result = await db.execute(
        select(DagDefinition).where(DagDefinition.id == dag_id)
    )
    d = result.scalar_one_or_none()
    if not d:
        return None
    if req.dag_name is not None:
        d.dag_name = req.dag_name
    if req.schedule is not None:
        d.schedule = req.schedule
    if req.description is not None:
        d.description = req.description
    if req.status is not None:
        d.status = req.status
    if req.nodes is not None:
        # replace nodes
        await db.execute(
            __import__("sqlalchemy").delete(DagNode).where(DagNode.dag_id == dag_id)
        )
        _add_nodes(db, dag_id, req.nodes)
    await db.commit()
    return await _reload(db, dag_id)


async def delete_dag(db: AsyncSession, dag_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(DagDefinition).where(DagDefinition.id == dag_id)
    )
    d = result.scalar_one_or_none()
    if not d:
        return False
    await db.delete(d)
    await db.commit()
    return True


async def deploy_dag(db: AsyncSession, dag_id: uuid.UUID) -> dict:
    """Generate the Airflow DAG file (nodes with dependencies) and upload via SFTP."""
    import paramiko

    from app.services.component_service import _load_config

    d = await _reload(db, dag_id)
    if not d:
        raise ValueError("DAG not found")
    nodes = d["nodes"]
    if not nodes:
        raise ValueError("DAG 至少需要一个任务节点")

    # Validate cycle-free dependency references
    node_names = {n["node_name"] for n in nodes}
    for n in nodes:
        for up in n["depends_on"]:
            if up not in node_names:
                raise ValueError(f"节点 {n['node_name']} 的上游依赖 {up} 不存在")

    # Build DAG file content
    lines = [
        f'"""DataMind workflow DAG: {d["dag_name"]}"""',
        "from airflow import DAG",
        "from airflow.operators.trigger_dagrun import TriggerDagRunOperator",
        "from airflow.utils.dates import days_ago",
        "",
        'default_args = {"owner": "datamind", "retries": 0}',
        "",
        "dag = DAG(",
        f'    dag_id="{d["dag_id"]}",',
        f'    description="{d["dag_name"]}",',
        f'    schedule="{d["schedule"]}",',
        "    start_date=days_ago(1),",
        "    catchup=False,",
        '    tags=["datamind", "workflow"],',
        "    default_args=default_args,",
        ")",
        "",
    ]
    op_vars = {}
    for i, n in enumerate(nodes):
        trigger_dag = "datax_sync" if n["task_type"] == "datax" else "spark_job"
        var = f"node_{i}"
        op_vars[n["node_name"]] = var
        lines.append(f'{var} = TriggerDagRunOperator(')
        lines.append(f'    task_id="{n["node_name"]}",')
        lines.append(f'    trigger_dag_id="{trigger_dag}",')
        lines.append(f'    conf={{"task_id": "{n["task_id"]}"}},')
        lines.append("    dag=dag,")
        lines.append(")")
        lines.append("")

    # Dependencies (A >> B means A runs before B)
    for n in nodes:
        var = op_vars[n["node_name"]]
        for up in n["depends_on"]:
            up_var = op_vars.get(up)
            if up_var:
                lines.append(f"{up_var} >> {var}")
    content = "\n".join(lines) + "\n"

    # Upload via SFTP
    config = await _load_config(db, "airflow")
    if not config:
        raise RuntimeError("Airflow component not configured")
    ssh_host = config.get("ssh_host") or "192.168.1.4"
    ssh_port = int(config.get("ssh_port") or 22)
    ssh_user = config.get("ssh_user") or "root"
    ssh_password = config.get("ssh_password") or ""
    dags_path = config.get("dags_path") or "/home/airflow/dags"
    if not ssh_password:
        raise ValueError("请先在 Airflow 组件配置中填写 SSH 密码")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ssh_host, port=ssh_port, username=ssh_user, password=ssh_password, timeout=15)
    sftp = client.open_sftp()
    try:
        remote = f"{dags_path.rstrip('/')}/{d['dag_id']}.py"
        with sftp.open(remote, "w") as f:
            f.write(content.encode("utf-8"))
    finally:
        sftp.close()
        client.close()

    # mark as deployed
    result = await db.execute(
        select(DagDefinition).where(DagDefinition.id == dag_id)
    )
    dd = result.scalar_one_or_none()
    if dd:
        dd.status = "deployed"
        await db.commit()

    return {"dag_id": d["dag_id"], "file": remote, "nodes": len(nodes), "content": content}


def _add_nodes(db: AsyncSession, dag_id: uuid.UUID, items: list) -> None:
    for i, n in enumerate(items):
        db.add(DagNode(
            dag_id=dag_id,
            node_name=n.node_name,
            task_type=n.task_type,
            task_id=uuid.UUID(n.task_id),
            depends_on=n.depends_on or [],
            sort_order=i,
        ))


async def _reload(db: AsyncSession, dag_id: uuid.UUID) -> dict | None:
    result = await db.execute(
        select(DagDefinition).where(DagDefinition.id == dag_id)
    )
    d = result.scalar_one_or_none()
    return _to_dict(d) if d else None


def _to_dict(d: DagDefinition) -> dict:
    return {
        "id": str(d.id),
        "dag_id": d.dag_id,
        "dag_name": d.dag_name,
        "schedule": d.schedule,
        "description": d.description,
        "status": d.status,
        "nodes": [
            {
                "node_name": n.node_name,
                "task_type": n.task_type,
                "task_id": str(n.task_id),
                "depends_on": n.depends_on or [],
            }
            for n in (d.nodes or [])
        ],
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "updated_at": d.updated_at.isoformat() if d.updated_at else None,
    }
