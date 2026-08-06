"""Cube 指标接口: 元数据 + 查询 + 健康检查。"""
from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.common import ResponseOK
from app.services import cube_service

router = APIRouter()


class CubeQuery(BaseModel):
    measures: list[str] = []
    dimensions: list[str] = []
    timeDimensions: list[dict] = []
    filters: list[dict] = []
    order: dict = {}
    limit: int = 10000


@router.get("/meta", response_model=ResponseOK[dict], summary="Cube元数据")
async def get_meta(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    try:
        result = await cube_service.get_meta(db)
        return ResponseOK(data=result)
    except RuntimeError as e:
        return ResponseOK(code=503, message=str(e))


@router.post("/load", response_model=ResponseOK[dict], summary="指标查询")
async def load_data(
    query: CubeQuery = Body(...),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        result = await cube_service.load_data(db, query.model_dump(exclude_none=True))
        return ResponseOK(data=result)
    except RuntimeError as e:
        return ResponseOK(code=503, message=str(e))


@router.get("/health", response_model=ResponseOK[dict], summary="健康检查")
async def health_check(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    healthy = await cube_service.health_check(db)
    return ResponseOK(data={"healthy": healthy})
