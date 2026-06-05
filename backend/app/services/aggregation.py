"""
短文本聚合服务

将同一视频下、同一时间窗口内的短评论聚合为伪文档，
缓解 B 站短评论（10-50字）带来的语义稀疏问题。
"""

import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.comment import Comment
from app.models.comment_group import CommentGroup

logger = logging.getLogger(__name__)

# 北京时间时区
CST = timezone(timedelta(hours=8))


class AggregationService:
    """短文本聚合服务。

    按 (video_id, time_window) 将已清洗/分词的评论合并为伪文档，
    提升主题建模时每条文档的语义丰富度。

    用法:
        async with AsyncSession(...) as db:
            service = AggregationService(db)
            count = await service.process(window_minutes=60, min_comments=3)
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def clear(self) -> int:
        """清空已有聚合数据。

        Returns:
            删除的记录数
        """
        result = await self.db.execute(delete(CommentGroup))
        await self.db.commit()
        deleted = result.rowcount
        logger.info("已清空 %d 条 CommentGroup 记录", deleted)
        return deleted

    async def process(
        self,
        window_minutes: int = 60,
        min_comments: int = 3,
    ) -> int:
        """执行短文本聚合。

        Args:
            window_minutes: 时间窗口大小（分钟），默认 60
            min_comments: 最少评论数，低于此阈值的组被丢弃

        Returns:
            创建的 CommentGroup 记录数
        """
        # 1. 清空旧数据
        await self.clear()

        # 2. 查询所有已清洗的评论
        result = await self.db.execute(
            select(
                Comment.id,
                Comment.video_id,
                Comment.create_time,
                Comment.cleaned_content,
                Comment.tokens_json,
            ).where(
                Comment.tokens_json.isnot(None),
                Comment.token_count > 0,
            )
        )
        rows = result.all()

        if not rows:
            logger.warning("没有已清洗的评论，跳过聚合")
            return 0

        # 3. 按 (video_id, time_window) 分组
        window_seconds = window_minutes * 60
        groups: dict[tuple[str, int], dict] = {}

        for comment_id, video_id, create_time, cleaned_content, tokens_json in rows:
            if not video_id or not create_time:
                continue

            # 时间窗口分桶
            window_key = create_time // window_seconds
            group_key = (video_id, window_key)

            if group_key not in groups:
                groups[group_key] = {
                    "video_id": video_id,
                    "time_window_start": datetime.fromtimestamp(
                        window_key * window_seconds, tz=CST
                    ),
                    "time_window_end": datetime.fromtimestamp(
                        (window_key + 1) * window_seconds, tz=CST
                    ),
                    "comment_count": 0,
                    "comment_ids": [],
                    "contents": [],
                    "all_tokens": [],
                }

            g = groups[group_key]
            g["comment_count"] += 1
            g["comment_ids"].append(comment_id)
            if cleaned_content:
                g["contents"].append(cleaned_content)

            # 解析并合并 tokens
            if tokens_json:
                try:
                    tokens = json.loads(tokens_json)
                    if isinstance(tokens, list):
                        g["all_tokens"].extend(tokens)
                except (json.JSONDecodeError, TypeError):
                    pass

        # 4. 过滤不足 min_comments 的组
        valid_groups = [
            g for g in groups.values() if g["comment_count"] >= min_comments
        ]

        if not valid_groups:
            logger.warning(
                "没有满足 min_comments=%d 的聚合组（共 %d 组）",
                min_comments,
                len(groups),
            )
            return 0

        # 5. 批量写入 CommentGroup
        import math
        batch_size = 500
        created = 0

        for i in range(0, len(valid_groups), batch_size):
            batch = valid_groups[i : i + batch_size]
            for g in batch:
                record = CommentGroup(
                    video_id=g["video_id"],
                    time_window_start=g["time_window_start"],
                    time_window_end=g["time_window_end"],
                    comment_count=g["comment_count"],
                    aggregated_content=" ".join(g["contents"]),
                    aggregated_tokens_json=json.dumps(
                        g["all_tokens"], ensure_ascii=False
                    ),
                    unique_comment_ids=json.dumps(
                        g["comment_ids"], ensure_ascii=False
                    ),
                    is_aggregated=True,
                )
                self.db.add(record)
                created += 1

            await self.db.commit()

        logger.info(
            "聚合完成: %d 组（从 %d 条评论，%d 个原始分组中），窗口=%d分钟，最少=%d条",
            created,
            len(rows),
            len(groups),
            window_minutes,
            min_comments,
        )
        return created

    async def get_status(self) -> dict:
        """获取当前聚合状态统计。

        Returns:
            dict，包含 total_groups, total_comments_aggregated,
            coverage_pct, distinct_videos, avg_group_size, max_group_size,
            size_distribution
        """
        from sqlalchemy import func

        # 总聚合组数
        result = await self.db.execute(
            select(func.count(CommentGroup.id))
        )
        total_groups = result.scalar() or 0

        # 总评论数（已清洗的）
        result = await self.db.execute(
            select(func.count(Comment.id)).where(
                Comment.tokens_json.isnot(None),
                Comment.token_count > 0,
            )
        )
        total_comments = result.scalar() or 0

        if total_groups == 0:
            return {
                "total_groups": 0,
                "total_comments_aggregated": 0,
                "total_comments_total": total_comments,
                "coverage_pct": 0.0,
                "distinct_videos": 0,
                "avg_group_size": 0.0,
                "max_group_size": 0,
                "size_distribution": [],
            }

        # 聚合覆盖的评论数和视频数
        result = await self.db.execute(
            select(
                func.sum(CommentGroup.comment_count),
                func.count(func.distinct(CommentGroup.video_id)),
                func.avg(CommentGroup.comment_count),
                func.max(CommentGroup.comment_count),
            )
        )
        row = result.one()
        total_aggregated = row[0] or 0
        distinct_videos = row[1] or 0
        avg_group_size = round(float(row[2] or 0), 1)
        max_group_size = row[3] or 0

        coverage_pct = round(total_aggregated / total_comments * 100, 1) if total_comments > 0 else 0.0

        # 组大小分布（直方图桶）
        result = await self.db.execute(
            select(
                CommentGroup.comment_count,
                func.count(CommentGroup.id),
            ).group_by(CommentGroup.comment_count).order_by(CommentGroup.comment_count)
        )
        size_distribution = [
            {"comment_count": row[0], "group_count": row[1]}
            for row in result.all()
        ]

        return {
            "total_groups": total_groups,
            "total_comments_aggregated": total_aggregated,
            "total_comments_total": total_comments,
            "coverage_pct": coverage_pct,
            "distinct_videos": distinct_videos,
            "avg_group_size": avg_group_size,
            "max_group_size": max_group_size,
            "size_distribution": size_distribution,
        }

    @staticmethod
    def get_config() -> dict:
        """获取当前聚合配置（从 settings 读取）。

        Returns:
            dict，包含 enabled, window_minutes, min_comments
        """
        return {
            "enabled": settings.aggregation_enabled,
            "window_minutes": settings.aggregation_window_minutes,
            "min_comments": settings.aggregation_min_comments,
        }
