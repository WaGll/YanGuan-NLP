"""
聚合管理 API 路由

提供短文本聚合的触发、状态查询和运行时配置更新。
"""

import time

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config import settings
from app.schemas.aggregation import (
    AggregationConfigRequest,
    AggregationConfigResponse,
    AggregationRunResponse,
    AggregationStatusResponse,
)
from app.schemas.common import APIResponse
from app.services.aggregation import AggregationService

router = APIRouter(tags=["聚合管理"])


@router.post("/aggregation/run")
async def run_aggregation(
    window_minutes: int = Query(120, ge=10, le=1440, description="时间窗口大小（分钟）"),
    min_comments: int = Query(2, ge=1, le=100, description="每组最少评论数"),
    db: AsyncSession = Depends(get_db),
):
    """触发重新聚合。

    将清空现有聚合数据，按指定参数重新分组。
    """
    t_start = time.monotonic()
    service = AggregationService(db)
    groups_created = await service.process(
        window_minutes=window_minutes,
        min_comments=min_comments,
    )
    elapsed = round(time.monotonic() - t_start, 2)

    return APIResponse(
        data=AggregationRunResponse(
            groups_created=groups_created,
            comments_processed=0,  # process() doesn't return this separately
            window_minutes=window_minutes,
            min_comments=min_comments,
            elapsed_seconds=elapsed,
        )
    )


@router.get("/aggregation/status")
async def get_aggregation_status(
    db: AsyncSession = Depends(get_db),
):
    """获取聚合状态统计。

    包含组数、覆盖率、视频数、组大小分布等信息。
    """
    service = AggregationService(db)
    status = await service.get_status()
    return APIResponse(data=AggregationStatusResponse(**status))


@router.get("/aggregation/config")
async def get_aggregation_config():
    """获取当前聚合配置。"""
    cfg = AggregationService.get_config()
    return APIResponse(data=AggregationConfigResponse(**cfg))


@router.put("/aggregation/config")
async def update_aggregation_config(
    body: AggregationConfigRequest,
):
    """运行时更新聚合配置（仅内存，重启后重置为环境变量值）。

    Note: 配置更新不会自动触发重新聚合，需调用 POST /aggregation/run。
    """
    if body.window_minutes is not None:
        settings.aggregation_window_minutes = body.window_minutes
    if body.min_comments is not None:
        settings.aggregation_min_comments = body.min_comments
    if body.enabled is not None:
        settings.aggregation_enabled = body.enabled

    cfg = AggregationService.get_config()
    return APIResponse(data=AggregationConfigResponse(**cfg))
