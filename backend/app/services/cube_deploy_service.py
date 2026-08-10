"""Cube datasource sync: apply a platform data source to the local Cube container."""
import asyncio
import os
from pathlib import Path
from typing import Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_value
from app.models import DataSource

CUBE_COMPOSE_DIR = os.environ.get("CUBE_COMPOSE_DIR", r"D:\DataMind")
CUBE_COMPOSE_FILE = os.path.join(CUBE_COMPOSE_DIR, "docker-compose.prod.yml")
CUBE_ENV_FILE = os.path.join(CUBE_COMPOSE_DIR, "cube", ".env")
CUBE_CONTAINER = os.environ.get("CUBE_CONTAINER_NAME", "datamind-cube")
DOCKER_SOCKET = os.environ.get("DOCKER_SOCKET", "/var/run/docker.sock")

# DataMind source type -> Cube DB driver
_TYPE_MAP = {
    "mysql": "mysql",
    "doris": "mysql",       # Doris speaks MySQL protocol
    "postgresql": "postgres",
}


async def _run_docker(args: list[str], timeout: int = 180) -> tuple[int, str, str]:
    """Run a docker CLI command; returns (returncode, stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        "docker", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return -1, "", "docker compose timed out"
    return proc.returncode or 0, out.decode("utf-8", errors="replace"), err.decode("utf-8", errors="replace")


async def _restart_cube_container(timeout: int = 180) -> tuple[int, str, str]:
    """Recreate the Cube container so the new env_file takes effect.

    Uses the Docker Engine API over the mounted unix socket when running inside
    the DataMind compose network; falls back to the docker CLI on the host.
    """
    if not os.path.exists(DOCKER_SOCKET):
        return await _run_docker(["compose", "-f", CUBE_COMPOSE_FILE, "up", "-d", "cube"])

    import httpx

    try:
        # Read the env file we just wrote and merge it over the old container env.
        env_updates: dict[str, str] = {}
        try:
            for raw in Path(CUBE_ENV_FILE).read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env_updates[k.strip()] = v.strip()
        except FileNotFoundError:
            return 1, "", f"env file not found: {CUBE_ENV_FILE}"

        transport = httpx.AsyncHTTPTransport(uds=DOCKER_SOCKET)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://docker", timeout=timeout
        ) as client:
            inspect = await client.get(f"/containers/{CUBE_CONTAINER}/json")
            if inspect.status_code == 404:
                return 1, "", f"cube container {CUBE_CONTAINER} not found"
            info = inspect.json()
            cfg = info.get("Config") or {}

            env_map: dict[str, str] = {}
            for kv in cfg.get("Env") or []:
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    env_map[k] = v
            env_map.update(env_updates)
            new_env = [f"{k}={v}" for k, v in env_map.items()]

            create_body = {
                "Image": cfg.get("Image"),
                "Env": new_env,
                "Cmd": cfg.get("Cmd"),
                "Entrypoint": cfg.get("Entrypoint"),
                "WorkingDir": cfg.get("WorkingDir"),
                "Labels": cfg.get("Labels") or {},
                "ExposedPorts": cfg.get("ExposedPorts") or {},
                "HostConfig": info.get("HostConfig") or {},
                "NetworkingConfig": info.get("NetworkingConfig") or {},
                "Tty": bool(cfg.get("Tty")),
                "OpenStdin": bool(cfg.get("OpenStdin")),
            }

            # Stop and remove the old container (ignore missing/stopped errors).
            for method, url in (
                ("POST", f"/containers/{CUBE_CONTAINER}/stop"),
                ("DELETE", f"/containers/{CUBE_CONTAINER}"),
            ):
                resp = await client.request(method, url)
                if resp.status_code not in (200, 204, 304, 404):
                    return resp.status_code, "", f"{method} {url}: {resp.text[:200]}"

            created = await client.post(
                f"/containers/create?name={CUBE_CONTAINER}", json=create_body
            )
            if created.status_code not in (200, 201):
                return created.status_code, "", f"create: {created.text[:300]}"
            started = await client.post(f"/containers/{CUBE_CONTAINER}/start")
            if started.status_code not in (200, 204, 304):
                return started.status_code, "", f"start: {started.text[:300]}"
        return 0, "", ""
    except Exception as e:
        logger.error(f"[cube] Docker API restart failed: {e}")
        return 1, "", str(e)


async def sync_cube_datasource(
    db: AsyncSession,
    datasource_id: str,
) -> dict:
    """Apply a platform data source to the Cube container (env + restart).

    Returns {"ok": bool, "message": str}.
    """
    import uuid

    try:
        ds_id = uuid.UUID(datasource_id)
    except (ValueError, TypeError):
        return {"ok": False, "message": "数据源 ID 无效"}

    result = await db.execute(select(DataSource).where(DataSource.id == ds_id))
    ds = result.scalar_one_or_none()
    if not ds:
        return {"ok": False, "message": "数据源不存在"}
    if ds.status != "active":
        return {"ok": False, "message": "数据源未启用"}
    if not ds.last_connection_ok:
        return {"ok": False, "message": "数据源未通过连接测试，请先测试连接"}

    cube_db_type = _TYPE_MAP.get(ds.source_type)
    if not cube_db_type:
        return {"ok": False, "message": f"数据源类型 {ds.source_type} 暂不支持 Cube 连接"}

    password = ""
    try:
        password = decrypt_value(ds.password_encrypted) or ""
    except Exception as e:
        logger.warning(f"[cube] decrypt datasource password failed: {e}")

    # write cube/.env consumed by docker compose (env_file)
    env_content = (
        "CUBEJS_DEV_MODE=true\n"
        f"CUBEJS_DB_TYPE={cube_db_type}\n"
        f"CUBEJS_DB_HOST={ds.host}\n"
        f"CUBEJS_DB_PORT={ds.port}\n"
        f"CUBEJS_DB_NAME={ds.database_name or ''}\n"
        f"CUBEJS_DB_USER={ds.username}\n"
        f"CUBEJS_DB_PASS={password}\n"
        "CUBEJS_API_SECRET=secret\n"
    )
    with open(CUBE_ENV_FILE, "w", encoding="utf-8") as f:
        f.write(env_content)

    # recreate the cube container so the new env takes effect
    code, out, err = await _restart_cube_container()
    if code != 0:
        logger.error(f"[cube] docker compose up failed: {err or out}")
        return {"ok": False, "message": f"Cube 容器重启失败: {(err or out).strip()[:200]}"}
    logger.info(f"[cube] datasource synced -> {ds.source_name} ({ds.source_type} {ds.host}:{ds.port})")
    return {"ok": True, "message": f"已同步数据源「{ds.source_name}」并重启 Cube 容器"}
