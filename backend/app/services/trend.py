"""
时序趋势分析服务

按时间粒度（月/周/日）聚合情感分数，生成时序趋势数据。
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.models.sentiment import SentimentResult

logger = logging.getLogger(__name__)

# 时间粒度到 SQL strftime 格式的映射
GRANULARITY_FORMAT: dict[str, str] = {
    "day": "%Y-%m-%d",
    "week": "%Y-%W",
    "month": "%Y-%m",
    "year": "%Y",
}


class TrendService:
    """时序趋势分析服务。

    按指定时间粒度聚合评论情感分数，生成可用于折线图的趋势数据。
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # 公开方法
    # ------------------------------------------------------------------

    async def compute_sentiment_trend(
        self, granularity: str = "month"
    ) -> list[dict[str, Any]]:
        """计算情感分数的时序趋势。

        按 granularity 对评论分组，计算每段时间桶的平均情感分数和评论数。

        Args:
            granularity: 时间粒度（day / week / month / year）

        Returns:
            [{bucket_start, bucket_end, value, comment_count}, ...]
        """
        fmt = GRANULARITY_FORMAT.get(granularity, "%Y-%m")

        # 查询 joint 数据，按时间桶分组计算平均值和分类计数
        result = await self.db.execute(
            select(
                func.strftime(
                    fmt,
                    func.datetime(Comment.create_time, "unixepoch", "localtime"),
                ).label("bucket"),
                func.avg(SentimentResult.snownlp_score).label("avg_score"),
                func.count(SentimentResult.id).label("cnt"),
                func.sum(
                    case((SentimentResult.sentiment_class == "positive", 1), else_=0)
                ).label("positive_count"),
                func.sum(
                    case((SentimentResult.sentiment_class == "neutral", 1), else_=0)
                ).label("neutral_count"),
                func.sum(
                    case((SentimentResult.sentiment_class == "negative", 1), else_=0)
                ).label("negative_count"),
            )
            .join(SentimentResult, Comment.id == SentimentResult.comment_id)
            .where(Comment.create_time > 0)
            .group_by("bucket")
            .order_by("bucket")
        )
        rows = result.all()
        if not rows:
            logger.warning("无评论数据，无法计算情感趋势")
            return []

        trend_data = []
        for (
            bucket_str,
            avg_score,
            comment_count,
            positive_count,
            neutral_count,
            negative_count,
        ) in rows:
            bucket_start, bucket_end = self._parse_bucket_range(
                bucket_str, granularity
            )
            trend_data.append({
                "bucket_start": bucket_start,
                "bucket_end": bucket_end,
                "avg_sentiment": round(float(avg_score), 4) if avg_score else 0.0,
                "comment_count": comment_count or 0,
                "positive_count": positive_count or 0,
                "neutral_count": neutral_count or 0,
                "negative_count": negative_count or 0,
            })

        logger.info(
            "情感趋势计算完成: %d 个时间桶, granularity=%s",
            len(trend_data),
            granularity,
        )
        return trend_data

    # ------------------------------------------------------------------
    # 私有方法
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_bucket_range(
        bucket_str: str, granularity: str
    ) -> tuple[str | None, str | None]:
        """将 strftime 输出的时间桶字符串解析为起止时间。

        Args:
            bucket_str: strftime 格式的时间桶标签
            granularity: 时间粒度

        Returns:
            (bucket_start, bucket_end) ISO 格式字符串
        """
        try:
            if granularity == "day":
                dt = datetime.strptime(bucket_str, "%Y-%m-%d")
                start = dt.strftime("%Y-%m-%dT00:00:00")
                end = (dt + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")
                return start, end
            elif granularity == "week":
                # strftime "%Y-%W" 格式: 年-周序号
                year, week = bucket_str.split("-")
                year = int(year)
                week = int(week)
                # ISO 周的第一天（ISO 周从周一开始）
                jan4 = datetime(year, 1, 4)
                start_of_week1 = jan4 - timedelta(days=jan4.isoweekday() - 1)
                start = start_of_week1 + timedelta(weeks=week - 1)
                end = start + timedelta(weeks=1)
                return start.strftime("%Y-%m-%dT00:00:00"), end.strftime(
                    "%Y-%m-%dT00:00:00"
                )
            elif granularity == "month":
                dt = datetime.strptime(bucket_str, "%Y-%m")
                start = dt.strftime("%Y-%m-01T00:00:00")
                # 下个月第一天
                if dt.month == 12:
                    next_month = datetime(dt.year + 1, 1, 1)
                else:
                    next_month = datetime(dt.year, dt.month + 1, 1)
                end = next_month.strftime("%Y-%m-01T00:00:00")
                return start, end
            else:
                return bucket_str, None
        except (ValueError, Exception):
            return bucket_str, None
