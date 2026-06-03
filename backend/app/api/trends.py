"""
趋势分析 API 路由

提供按时间粒度聚合的情感趋势时序数据。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.common import APIResponse
from app.services.trend import TrendService

router = APIRouter(tags=["趋势分析"])


@router.get("/trends")
async def get_trends(
    series_type: str = Query(
        "sentiment", description="趋势类型: sentiment / volume"
    ),
    granularity: str = Query(
        "month", description="时间粒度: day / week / month / year"
    ),
    db: AsyncSession = Depends(get_db),
):
    """获取情感分数的时序趋势数据。

    - **series_type**: 趋势类型，当前支持 sentiment
    - **granularity**: 时间聚合粒度
    - 返回每个时间桶的起止时间、平均情感分数和评论数量
    """
    service = TrendService(db)

    if series_type == "sentiment":
        trend_data = await service.compute_sentiment_trend(granularity=granularity)
    else:
        # 预留其他趋势类型的扩展点
        trend_data = []

    return APIResponse(data=trend_data)
