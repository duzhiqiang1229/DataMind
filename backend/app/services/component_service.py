"""Component config service: CRUD + health check + client factory."""
import json
import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.security import encrypt_value, decrypt_value
from app.models import ComponentConfig
from app.schemas.component import (
    ComponentConfigCreate, ComponentConfigUpdate, ComponentConfigResponse, HealthCheckResponse,
)

# --- client cache (per process) ---
_client_cache: dict[str, object] = {}


async def _load_config(db: AsyncSession, component_code: str) -> dict | None:
    """Load component config from DB and decrypt credentials."""
    result = await db.execute(
        select(ComponentConfig).where(ComponentConfig.component_code == component_code)
    )
    cfg = result.scalar_one_or_none()
    if not cfg:
        return None

    config = {
        "base_url": cfg.base_url,
        "auth_type": cfg.auth_type,
        **cfg.config_json,
    }
    # decrypt credentials
    if cfg.credentials_encrypted:
        try:
            creds = json.loads(decrypt_value(cfg.credentials_encrypted))
            config["credentials"] = creds
        except Exception as e:
            logger.warning(f"Failed to decrypt credentials for {component_code}: {e}")
            config["credentials"] = {}
    else:
        config["credentials"] = {}

    # Inside the DataMind compose network, use service DNS names. Host-facing
    # addresses can be unreachable from containers when their ports are bound
    # only to loopback or blocked by host firewall rules.
    if os.getenv("DATAMIND_IN_DOCKER") == "true":
        internal_urls = {
            "airflow": "http://airflow-api-server:8080",
            "cube": "http://cube:4000",
        }
        if component_code in internal_urls:
            config["base_url"] = internal_urls[component_code]

    return config


async def get_airflow_client(db: AsyncSession):
    """Get or create AirflowClient from DB config."""
    if "airflow" in _client_cache:
        return _client_cache["airflow"]

    from app.integrations.airflow_client import AirflowClient
    config = await _load_config(db, "airflow")
    if not config:
        raise RuntimeError("Airflow component not configured. Add it in system settings.")
    client = AirflowClient(config)
    _client_cache["airflow"] = client
    return client


async def get_doris_client(db: AsyncSession):
    """Get or create DorisClient from DB config."""
    if "doris" in _client_cache:
        return _client_cache["doris"]

    from app.integrations.doris_client import DorisClient
    config = await _load_config(db, "doris")
    if config:
        client = DorisClient(config)
    else:
        # Fallback: Doris component config removed — use the Doris data source
        # from data source management (source_type='doris').
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
            raise RuntimeError("Doris 未配置，请在数据源管理中配置 Doris 数据源")
        client = DorisClient({
            "base_url": f"http://{ds.host}:8030",
            "auth_type": "basic",
            "mysql_host": ds.host,
            "mysql_port": ds.port,
            "http_port": 8030,
            "credentials": {
                "username": ds.username,
                "password": decrypt_value(ds.password_encrypted),
            },
        })
    _client_cache["doris"] = client
    return client


async def get_cube_client(db: AsyncSession):
    """Get or create CubeClient from DB config."""
    if "cube" in _client_cache:
        return _client_cache["cube"]

    from app.integrations.cube_client import CubeClient
    config = await _load_config(db, "cube")
    if not config:
        raise RuntimeError("Cube component not configured.")
    client = CubeClient(config)
    _client_cache["cube"] = client
    return client


def clear_client_cache(component_code: str | None = None):
    """Clear cached client(s) — call after config update."""
    if component_code:
        _client_cache.pop(component_code, None)
    else:
        _client_cache.clear()


async def list_components(db: AsyncSession, page: int, page_size: int) -> tuple[list, int]:
    """Paginated list of component configs."""
    total_q = await db.execute(select(func.count(ComponentConfig.id)))
    total = total_q.scalar_one()
    result = await db.execute(
        select(ComponentConfig)
        .order_by(ComponentConfig.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return result.scalars().all(), total


async def get_component(db: AsyncSession, component_id: uuid.UUID) -> ComponentConfig | None:
    result = await db.execute(select(ComponentConfig).where(ComponentConfig.id == component_id))
    return result.scalar_one_or_none()


async def get_component_by_code(db: AsyncSession, component_code: str) -> ComponentConfig | None:
    """Get component config by code (e.g. 'airflow', 'doris')."""
    result = await db.execute(
        select(ComponentConfig).where(ComponentConfig.component_code == component_code)
    )
    return result.scalar_one_or_none()


# --- Component metadata for dedicated config pages ---
COMPONENT_META = {
    "airflow":      {"name": "Airflow 调度服务",    "type": "scheduler",  "icon": "Timer"},
    "doris":        {"name": "Doris 数仓引擎",      "type": "olap",       "icon": "Coin"},
    "cube":         {"name": "Cube 语义指标引擎",   "type": "semantic",   "icon": "DataAnalysis"},
}


async def upsert_component_by_code(
    db: AsyncSession, component_code: str, req: ComponentConfigUpdate
) -> ComponentConfig:
    """Create or update component config by code (upsert)."""
    existing = await get_component_by_code(db, component_code)
    meta = COMPONENT_META.get(component_code, {})

    if existing:
        # Update existing
        if req.component_name is not None:
            existing.component_name = req.component_name
        if req.base_url is not None:
            existing.base_url = req.base_url
        if req.config_json is not None:
            existing.config_json = req.config_json
        if req.auth_type is not None:
            existing.auth_type = req.auth_type
        if req.status is not None:
            existing.status = req.status
        if req.credentials is not None:
            existing.credentials_encrypted = encrypt_value(json.dumps(req.credentials))
        cfg = existing
    else:
        # Create new
        cfg = ComponentConfig(
            component_code=component_code,
            component_name=req.component_name or meta.get("name", component_code),
            component_type=meta.get("type", "unknown"),
            base_url=req.base_url or "",
            config_json=req.config_json or {},
            auth_type=req.auth_type or "none",
            status=req.status or "active",
        )
        if req.credentials:
            cfg.credentials_encrypted = encrypt_value(json.dumps(req.credentials))
        db.add(cfg)

    await db.commit()
    await db.refresh(cfg)
    clear_client_cache(component_code)

    # Cube: apply the selected platform datasource to the Cube container
    if component_code == "cube" and (cfg.config_json or {}).get("datasource_id"):
        try:
            from app.services.cube_deploy_service import sync_cube_datasource

            sync = await sync_cube_datasource(db, str(cfg.config_json["datasource_id"]))
            if sync.get("ok"):
                logger.info(f"[component] {sync.get('message')}")
            else:
                logger.warning(f"[component] cube datasource sync failed: {sync.get('message')}")
        except Exception as e:
            logger.warning(f"[component] cube datasource sync exception: {e}")

    return cfg


async def create_component(db: AsyncSession, req: ComponentConfigCreate) -> ComponentConfig:
    cfg = ComponentConfig(
        component_code=req.component_code,
        component_name=req.component_name,
        component_type=req.component_type,
        base_url=req.base_url,
        config_json=req.config_json,
        auth_type=req.auth_type,
    )
    if req.credentials:
        cfg.credentials_encrypted = encrypt_value(json.dumps(req.credentials))
    db.add(cfg)
    await db.commit()
    await db.refresh(cfg)
    clear_client_cache(req.component_code)
    return cfg


async def update_component(
    db: AsyncSession, component_id: uuid.UUID, req: ComponentConfigUpdate
) -> ComponentConfig | None:
    cfg = await get_component(db, component_id)
    if not cfg:
        return None

    if req.component_name is not None:
        cfg.component_name = req.component_name
    if req.base_url is not None:
        cfg.base_url = req.base_url
    if req.config_json is not None:
        cfg.config_json = req.config_json
    if req.auth_type is not None:
        cfg.auth_type = req.auth_type
    if req.status is not None:
        cfg.status = req.status
    if req.credentials is not None:
        cfg.credentials_encrypted = encrypt_value(json.dumps(req.credentials))

    await db.commit()
    await db.refresh(cfg)
    clear_client_cache(cfg.component_code)
    return cfg


async def delete_component(db: AsyncSession, component_id: uuid.UUID) -> bool:
    cfg = await get_component(db, component_id)
    if not cfg:
        return False
    code = cfg.component_code
    await db.delete(cfg)
    await db.commit()
    clear_client_cache(code)
    return True


async def health_check(db: AsyncSession, component_code: str) -> HealthCheckResponse:
    """Run health check on a component."""
    result = await db.execute(
        select(ComponentConfig).where(ComponentConfig.component_code == component_code)
    )
    cfg = result.scalar_one_or_none()
    if not cfg:
        return HealthCheckResponse(
            component_code=component_code,
            component_name="unknown",
            healthy=False,
            message="Component not configured",
            checked_at=datetime.now(timezone.utc),
        )

    try:
        client_map = {
            "airflow": get_airflow_client,
            "doris": get_doris_client,
            "cube": get_cube_client,
        }
        getter = client_map.get(component_code)
        if not getter:
            return HealthCheckResponse(
                component_code=component_code,
                component_name=cfg.component_name,
                healthy=False,
                message=f"Unknown component type: {component_code}",
                checked_at=datetime.now(timezone.utc),
            )

        client = await getter(db)
        healthy = await client.health_check()

        # update last check result
        await db.execute(
            update(ComponentConfig)
            .where(ComponentConfig.id == cfg.id)
            .values(last_check_at=datetime.now(timezone.utc), last_check_ok=healthy)
        )
        await db.commit()

        return HealthCheckResponse(
            component_code=component_code,
            component_name=cfg.component_name,
            healthy=healthy,
            message="OK" if healthy else "Connection failed",
            checked_at=datetime.now(timezone.utc),
        )
    except Exception as e:
        return HealthCheckResponse(
            component_code=component_code,
            component_name=cfg.component_name,
            healthy=False,
            message=str(e),
            checked_at=datetime.now(timezone.utc),
        )
