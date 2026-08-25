"""Administration API for DataMind MCP clients, tokens and audit logs."""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.schemas.common import ResponseOK
from app.services import mcp_service


router = APIRouter(dependencies=[Depends(require_role("admin"))])


class McpClientCreate(BaseModel):
    client_name: str = Field(..., min_length=1, max_length=100)
    client_code: str = Field(..., min_length=2, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    service_user_id: uuid.UUID
    scopes: list[str] = Field(default_factory=lambda: list(mcp_service.DEFAULT_SCOPES))


class McpTokenCreate(BaseModel):
    token_name: str = Field(..., min_length=1, max_length=100)
    expires_at: datetime | None = None


class McpClientScopesUpdate(BaseModel):
    scopes: list[str]


@router.get("/capabilities", response_model=ResponseOK[dict], summary="MCP功能清单")
async def capabilities():
    from app.mcp.server import build_tool_catalog
    return ResponseOK(data=await build_tool_catalog())


@router.get("/clients", response_model=ResponseOK[list[dict]], summary="MCP客户端列表")
async def clients(db: AsyncSession = Depends(get_db)):
    return ResponseOK(data=await mcp_service.list_clients(db))


@router.post("/clients", response_model=ResponseOK[dict], summary="创建MCP客户端")
async def create_client(body: McpClientCreate, db: AsyncSession = Depends(get_db), user=Depends(require_role("admin"))):
    try:
        data = await mcp_service.create_client(
            db, body.client_name, body.client_code, body.service_user_id, body.scopes, user.id,
        )
        return ResponseOK(data=data)
    except ValueError as exc:
        return ResponseOK(code=400, message=str(exc))


@router.put("/clients/{client_id}/scopes", response_model=ResponseOK[dict], summary="更新MCP客户端授权范围")
async def update_client_scopes(client_id: uuid.UUID, body: McpClientScopesUpdate, db: AsyncSession = Depends(get_db)):
    try:
        return ResponseOK(data=await mcp_service.update_client_scopes(db, client_id, body.scopes))
    except ValueError as exc:
        return ResponseOK(code=400, message=str(exc))


@router.post("/clients/{client_id}/tokens", response_model=ResponseOK[dict], summary="生成MCP Token（仅展示一次）")
async def issue_token(client_id: uuid.UUID, body: McpTokenCreate, db: AsyncSession = Depends(get_db)):
    try:
        return ResponseOK(data=await mcp_service.issue_token(db, client_id, body.token_name, body.expires_at))
    except ValueError as exc:
        return ResponseOK(code=404, message=str(exc))


@router.get("/clients/{client_id}/tokens", response_model=ResponseOK[list[dict]], summary="MCP Token列表")
async def tokens(client_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return ResponseOK(data=await mcp_service.list_tokens(db, client_id))


@router.delete("/clients/{client_id}/tokens/{token_id}", response_model=ResponseOK, summary="吊销MCP Token")
async def revoke_token(client_id: uuid.UUID, token_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    if not await mcp_service.revoke_token(db, client_id, token_id):
        return ResponseOK(code=404, message="MCP Token不存在")
    return ResponseOK(message="MCP Token已吊销")


@router.get("/tool-calls", response_model=ResponseOK[list[dict]], summary="MCP工具调用日志")
async def tool_calls(limit: int = Query(100, ge=1, le=500), db: AsyncSession = Depends(get_db)):
    return ResponseOK(data=await mcp_service.list_tool_calls(db, limit))


@router.get("/change-sets", response_model=ResponseOK[list[dict]], summary="MCP变更集列表")
async def change_sets(
    status: str | None = Query(None), limit: int = Query(200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    return ResponseOK(data=await mcp_service.list_change_sets_admin(db, status, limit))


@router.get("/change-sets/{change_set_id}", response_model=ResponseOK[dict], summary="MCP变更集详情")
async def change_set_detail(change_set_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    data = await mcp_service.get_change_set_admin(db, change_set_id)
    if not data:
        return ResponseOK(code=404, message="变更集不存在")
    return ResponseOK(data=data)


@router.post("/change-sets/{change_set_id}/validate", response_model=ResponseOK[dict], summary="校验MCP变更集")
async def validate_change_set(
    change_set_id: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(require_role("admin")),
):
    try:
        return ResponseOK(data=await mcp_service.validate_change_set_admin(db, change_set_id, user.id))
    except ValueError as exc:
        return ResponseOK(code=400, message=str(exc))


@router.post("/change-sets/{change_set_id}/commit", response_model=ResponseOK[dict], summary="确认提交MCP变更集")
async def commit_change_set(
    change_set_id: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(require_role("admin")),
):
    try:
        return ResponseOK(data=await mcp_service.commit_change_set_admin(db, change_set_id, user.id))
    except ValueError as exc:
        return ResponseOK(code=400, message=str(exc))


@router.post("/change-sets/{change_set_id}/discard", response_model=ResponseOK[dict], summary="废弃MCP变更集")
async def discard_change_set(
    change_set_id: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(require_role("admin")),
):
    try:
        return ResponseOK(data=await mcp_service.discard_change_set_admin(db, change_set_id, user.id))
    except ValueError as exc:
        return ResponseOK(code=400, message=str(exc))
