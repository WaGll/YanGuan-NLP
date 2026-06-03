"""
通用响应模型

提供统一的 API 响应格式，包括单条/列表/分页响应。
"""

import math
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """通用 API 响应模型。

    所有 API 返回统一使用此格式，便于前端统一处理。

    示例:
        {
            "code": 200,
            "message": "success",
            "data": { ... }
        }
    """

    code: int = Field(default=200, description="状态码，HTTP 标准")
    message: str = Field(default="success", description="提示信息")
    data: Optional[T] = Field(default=None, description="响应数据")


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应模型。

    用于返回列表数据时附带分页元信息。

    示例:
        {
            "items": [...],
            "total": 100,
            "page": 1,
            "page_size": 20,
            "pages": 5
        }
    """

    items: list[T] = Field(default_factory=list, description="当前页数据列表")
    total: int = Field(default=0, description="总记录数")
    page: int = Field(default=1, ge=1, description="当前页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页记录数")

    @property
    def pages(self) -> int:
        """总页数。"""
        return max(1, math.ceil(self.total / self.page_size))
