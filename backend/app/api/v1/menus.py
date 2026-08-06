"""菜单管理接口: 树形CRUD。"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.common import ResponseOK
from app.services import menu_service

router = APIRouter()


class MenuCreate(BaseModel):
    parent_id: Optional[str] = None
    menu_name: str = Field(..., max_length=50)
    menu_type: str = Field(..., description="directory/menu/button")
    route_path: Optional[str] = None
    component: Optional[str] = None
    icon: Optional[str] = None
    sort_order: int = 0
    visible: bool = True


class MenuUpdate(BaseModel):
    parent_id: Optional[str] = None
    menu_name: Optional[str] = None
    menu_type: Optional[str] = None
    route_path: Optional[str] = None
    component: Optional[str] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = None
    visible: Optional[bool] = None
    status: Optional[str] = None


@router.get("/tree", response_model=ResponseOK[list[dict]], summary="菜单树")
async def get_menu_tree(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    tree = await menu_service.get_menu_tree(db)
    return ResponseOK(data=tree)


@router.post("", response_model=ResponseOK[dict], summary="新增菜单")
async def create_menu(req: MenuCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await menu_service.create_menu(
        db, req.parent_id, req.menu_name, req.menu_type,
        req.route_path, req.component, req.icon, req.sort_order, req.visible,
    )
    return ResponseOK(data=result)


@router.put("/{menu_id}", response_model=ResponseOK[dict], summary="更新菜单")
async def update_menu(menu_id: str, req: MenuUpdate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await menu_service.update_menu(db, uuid.UUID(menu_id), **req.model_dump())
    if not result:
        return ResponseOK(code=404, message="Menu not found")
    return ResponseOK(data=result)


@router.delete("/{menu_id}", response_model=ResponseOK, summary="删除菜单")
async def delete_menu(menu_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    ok = await menu_service.delete_menu(db, uuid.UUID(menu_id))
    if not ok:
        return ResponseOK(code=404, message="Menu not found")
    return ResponseOK()
