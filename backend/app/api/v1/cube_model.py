"""Cube 建模接口: 读取/生成/删除 Cube 与 View 模型文件。"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.common import ResponseOK
from app.services import cube_model_service

router = APIRouter()


class CubePayload(BaseModel):
    name: str
    title: str = ""
    sql_table: str = ""
    sql: str = ""
    data_source: str = "default"
    joins: list[dict] = []
    dimensions: list[dict] = []
    measures: list[dict] = []
    segments: list[dict] = []


class ViewPayload(BaseModel):
    name: str
    title: str = ""
    cubes: list[dict] = []


@router.get("/entities", response_model=ResponseOK[dict], summary="Cube 模型实体列表")
async def list_entities(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return ResponseOK(data=cube_model_service.list_models())


@router.get("/cubes/{name}", response_model=ResponseOK[dict], summary="Cube 详情")
async def get_cube(name: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    cube = cube_model_service.get_cube(name)
    if not cube:
        return ResponseOK(code=404, message="Cube 不存在")
    return ResponseOK(data=cube)


@router.post("/cubes", response_model=ResponseOK[dict], summary="保存 Cube")
async def save_cube(body: CubePayload, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    try:
        cube = cube_model_service.save_cube(body.model_dump())
    except ValueError as e:
        return ResponseOK(code=400, message=str(e))
    refresh = await cube_model_service.refresh_cube()
    return ResponseOK(data={**cube, "refresh": refresh})


@router.delete("/cubes/{name}", response_model=ResponseOK, summary="删除 Cube")
async def delete_cube(name: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    ok = cube_model_service.delete_cube(name)
    if not ok:
        return ResponseOK(code=404, message="Cube 不存在")
    await cube_model_service.refresh_cube()
    return ResponseOK()


@router.post("/views", response_model=ResponseOK[dict], summary="保存 View")
async def save_view(body: ViewPayload, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    try:
        view = cube_model_service.save_view(body.model_dump())
    except ValueError as e:
        return ResponseOK(code=400, message=str(e))
    refresh = await cube_model_service.refresh_cube()
    return ResponseOK(data={**view, "refresh": refresh})


@router.delete("/views/{name}", response_model=ResponseOK, summary="删除 View")
async def delete_view(name: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    ok = cube_model_service.delete_view(name)
    if not ok:
        return ResponseOK(code=404, message="View 不存在")
    await cube_model_service.refresh_cube()
    return ResponseOK()


@router.post("/refresh", response_model=ResponseOK[dict], summary="刷新 Cube 模型")
async def refresh(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return ResponseOK(data=await cube_model_service.refresh_cube())
