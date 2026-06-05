# Template: 新建 API 端点

## 使用说明

复制此模板创建新的 API 端点文件。替换 `{{placeholders}}`。

## 文件位置
`backend/app/api/{{module_name}}.py`

## 模板

```python
"""
{{模块中文名}} API 路由

提供 {{功能描述}} 的 REST API 端点。
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.{{model_file}} import {{ModelName}}
from app.schemas.common import APIResponse, PaginatedResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["{{标签名}}"])


# ---------------------------------------------------------------------------
# GET — 获取列表（分页）
# ---------------------------------------------------------------------------
@router.get("/{{endpoint_path}}", response_model=APIResponse[PaginatedResponse[dict]])
async def list_{{items}}(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """获取 {{项目名}} 列表，支持分页。

    Args:
        page: 页码（从 1 开始）
        page_size: 每页记录数（1~100）
        db: 数据库会话

    Returns:
        分页的 {{项目名}} 列表
    """
    # 查询总数
    count_query = select(func.count({{ModelName}}.id))
    total = (await db.execute(count_query)).scalar() or 0

    # 分页查询
    offset = (page - 1) * page_size
    query = (
        select({{ModelName}})
        .offset(offset)
        .limit(page_size)
        .order_by({{ModelName}}.id.desc())
    )
    result = await db.execute(query)
    items = result.scalars().all()

    # 序列化
    items_data = [serialize_{{item}}(item) for item in items]

    paginated = PaginatedResponse(
        items=items_data,
        total=total,
        page=page,
        page_size=page_size,
    )
    return APIResponse(data=paginated)


# ---------------------------------------------------------------------------
# GET — 获取单个详情
# ---------------------------------------------------------------------------
@router.get("/{{endpoint_path}}/{{'{'}item_id{'}'}}", response_model=APIResponse[dict])
async def get_{{item}}(
    item_id: int,
    db: AsyncSession = Depends(get_db),
):
    """根据 ID 获取 {{项目名}} 详情。

    Args:
        item_id: {{项目名}} ID
        db: 数据库会话

    Returns:
        {{项目名}} 详情数据

    Raises:
        HTTPException 404: {{项目名}}不存在
    """
    query = select({{ModelName}}).where({{ModelName}}.id == item_id)
    result = await db.execute(query)
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(status_code=404, detail="{{项目名}}不存在")

    return APIResponse(data=serialize_{{item}}(item))


# ---------------------------------------------------------------------------
# POST — 创建（如有创建需求）
# ---------------------------------------------------------------------------
# @router.post("/{{endpoint_path}}", response_model=APIResponse[dict], status_code=201)
# async def create_{{item}}(
#     body: {{CreateSchema}},
#     db: AsyncSession = Depends(get_db),
# ):
#     ...


# ---------------------------------------------------------------------------
# 序列化辅助函数（放在模块底部）
# ---------------------------------------------------------------------------
def serialize_{{item}}(item: {{ModelName}}) -> dict:
    """将 ORM 模型序列化为字典。"""
    return {
        "id": item.id,
        # 添加其他字段...
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }
```

## 清单

添加新端点时需要检查：
- [ ] 文件放在 `backend/app/api/` 下
- [ ] router 使用 `APIRouter(tags=["..."])` 
- [ ] 所有响应包裹在 `APIResponse` 中
- [ ] 使用 `Depends(get_db)` 获取数据库会话
- [ ] 实现 4 种状态：正常、空数据、参数错误(422)、资源不存在(404)
- [ ] 在 `backend/app/main.py` 中注册路由: `app.include_router(xxx_router, prefix="/api")`
- [ ] 添加对应的测试文件 `backend/tests/test_api/test_{{module_name}}.py`
