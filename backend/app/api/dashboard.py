"""
仪表盘 API 路由

提供数据概览统计信息，包括评论总数、用户数、时间范围等。
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.comment import Comment
from app.schemas.common import APIResponse
from app.schemas.dashboard import DashboardOverview

router = APIRouter(tags=["仪表盘"])


@router.get("/dashboard", response_model=APIResponse[DashboardOverview])
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DashboardOverview]:
    """获取数据仪表盘概览统计。

    返回评论总数、独立用户数、时间范围和平均情感分数等基础指标。
    """
    # 总评论数
    total_result = await db.execute(select(func.count(Comment.id)))
    total_comments: int = total_result.scalar() or 0

    # 独立用户数（基于 user_id 去重）
    user_result = await db.execute(
        select(func.count(func.distinct(Comment.user_id))).where(
            Comment.user_id.isnot(None)
        )
    )
    unique_users: int = user_result.scalar() or 0

    # 时间范围（Unix 时间戳 → datetime）
    time_min_result = await db.execute(
        select(func.min(Comment.create_time)).where(Comment.create_time > 0)
    )
    time_max_result = await db.execute(
        select(func.max(Comment.create_time)).where(Comment.create_time > 0)
    )
    date_range_start: datetime | None = None
    date_range_end: datetime | None = None
    min_ts = time_min_result.scalar()
    max_ts = time_max_result.scalar()
    if min_ts:
        try:
            date_range_start = datetime.fromtimestamp(min_ts)
        except (OSError, ValueError):
            pass
    if max_ts:
        try:
            date_range_end = datetime.fromtimestamp(max_ts)
        except (OSError, ValueError):
            pass

    # 平均情感分数（后续分析阶段填充，此处返回默认值 0.0）
    avg_sentiment: float = 0.0
    try:
        from app.models.sentiment import SentimentResult  # noqa: F811
        avg_result = await db.execute(select(func.avg(SentimentResult.snownlp_score)))
        avg_val = avg_result.scalar()
        if avg_val is not None:
            avg_sentiment = round(float(avg_val), 4)
    except Exception:
        pass

    overview = DashboardOverview(
        total_comments=total_comments,
        unique_users=unique_users,
        date_range_start=date_range_start,
        date_range_end=date_range_end,
        avg_sentiment=avg_sentiment,
    )

    return APIResponse(data=overview)
