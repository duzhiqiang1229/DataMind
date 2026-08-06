"""通用响应模型: 统一响应包装、分页响应。"""
from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel, Field


T = TypeVar("T")


class ResponseBase(BaseModel):
    """统一响应包装。"""
    code: int = 200
    message: str = "success"


class ResponseOK(ResponseBase, Generic[T]):
    """简单成功响应，支持泛型: ResponseOK[DataType]。"""
    data: Optional[T] = None


class ResponseError(ResponseBase):
    """错误响应。"""
    data: Optional[Any] = None


class PageResult(BaseModel, Generic[T]):
    """分页结果。"""
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(cls, items: list, total: int, page: int, page_size: int):
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class PageResponse(ResponseBase, Generic[T]):
    """分页响应。"""
    data: PageResult[T]
