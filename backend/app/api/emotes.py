"""
表情分析 API 路由

提供 B站方括号表情的频率分布、情感相关性、时间趋势等分析接口。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.common import APIResponse
from app.services.emote import EmoteService

router = APIRouter(tags=["表情分析"])


@router.get("/emotes")
async def get_emotes(
    sort_by: str = Query("frequency", description="排序方式: frequency / comment_count"),
    limit: int = Query(50, ge=1, le=200, description="返回数量"),
    sentiment: str = Query("all", description="情感过滤: positive / negative / neutral / all"),
    db: AsyncSession = Depends(get_db),
):
    """获取表情频率分布及情感统计。

    返回表情排行、情感分布饼图数据及总体统计。
    """
    service = EmoteService(db)
    sentiment_filter = None if sentiment == "all" else sentiment
    data = await service.get_frequency_distribution(
        sort_by=sort_by,
        limit=limit,
        sentiment_filter=sentiment_filter,
    )
    return APIResponse(data=data)


@router.get("/emotes/sentiment")
async def get_emote_sentiment_correlation(
    db: AsyncSession = Depends(get_db),
):
    """获取表情情感与文本情感的交叉分析。

    对比每种表情的固有情感标签与包含该表情的评论的实际文本情感分，
    计算 sentiment_delta（正值=文本比表情更正面）。
    """
    service = EmoteService(db)
    data = await service.get_sentiment_correlation()
    return APIResponse(data=data)


@router.get("/emotes/wordcloud")
async def get_emote_wordcloud(
    limit: int = Query(100, ge=1, le=200, description="返回数量"),
    db: AsyncSession = Depends(get_db),
):
    """获取表情词云数据（兼容 WordCloudChart 组件）。"""
    service = EmoteService(db)
    data = await service.get_wordcloud_data(limit=limit)
    return APIResponse(data=data)


@router.get("/emotes/{name}")
async def get_emote_detail(
    name: str,
    db: AsyncSession = Depends(get_db),
):
    """获取单个表情详情，含评论样例和平均文本情感分。"""
    service = EmoteService(db)
    data = await service.get_emote_detail(name)
    if data is None:
        return APIResponse(code=404, message=f"表情 '{name}' 不存在", data=None)
    return APIResponse(data=data)


@router.get("/emotes/{name}/timeline")
async def get_emote_timeline(
    name: str,
    granularity: str = Query("month", description="聚合粒度: month / week"),
    db: AsyncSession = Depends(get_db),
):
    """获取指定表情的时间趋势数据。"""
    service = EmoteService(db)
    data = await service.get_emote_timeline(name, granularity=granularity)
    return APIResponse(data=data)
