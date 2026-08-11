"""Internal allow-listed Docker executor.

This process is the only DataMind service with access to the Docker socket.
It deliberately exposes no generic command or container-name parameters.
"""
import hmac

from fastapi import Depends, FastAPI, Header, HTTPException

from app.core.config import settings
from app.services.cube_deploy_service import (
    _restart_cube_container,
    restart_cube_container,
)


app = FastAPI(
    title="DataMind Restricted Executor",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


def require_executor_token(x_executor_token: str = Header(...)) -> None:
    if len(settings.EXECUTOR_TOKEN) < 24:
        raise HTTPException(status_code=503, detail="Executor token is not configured")
    if not hmac.compare_digest(x_executor_token, settings.EXECUTOR_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid executor token")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "datamind-executor"}


@app.post("/v1/cube/restart", dependencies=[Depends(require_executor_token)])
async def restart_cube() -> dict:
    code, stdout, stderr = await restart_cube_container()
    return {"code": code, "stdout": stdout, "stderr": stderr}


@app.post("/v1/cube/recreate", dependencies=[Depends(require_executor_token)])
async def recreate_cube() -> dict:
    code, stdout, stderr = await _restart_cube_container()
    return {"code": code, "stdout": stdout, "stderr": stderr}
