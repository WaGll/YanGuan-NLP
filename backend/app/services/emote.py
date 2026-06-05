"""
表情分析服务

提供 B站方括号表情的提取、存储、频率统计和情感交叉分析。
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import case, delete, func, select, text
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.models.emote import CommentEmote, EmoteType
from app.models.sentiment import SentimentResult
from app.services.sentiment import NEGATIVE_THRESHOLD, POSITIVE_THRESHOLD
from app.utils.emote import extract_emotes
from app.utils.resources import NLPResources

logger = logging.getLogger(__name__)


class EmoteService:
    """表情分析服务。

    从评论原始 content 中提取 B站表情，存储到数据库，
    并提供频率分布、情感相关性、时间趋势等分析接口。
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # 数据提取与存储
    # ------------------------------------------------------------------

    async def extract_and_store_all(self, batch_size: int = 500) -> dict:
        """从所有评论中提取表情并持久化到数据库。

        批处理所有评论，从原始 content 提取方括号表情，
        upsert 到 emote_types 表并插入 comment_emotes 关联表。

        Args:
            batch_size: 每批处理的评论数

        Returns:
            {"distinct_emotes": int, "total_occurrences": int}
        """
        resources = NLPResources.get_instance()

        # 1) 清空旧数据
        await self.db.execute(delete(CommentEmote))
        await self.db.execute(delete(EmoteType))
        await self.db.flush()

        # 2) 批量查询所有评论
        result = await self.db.execute(
            select(Comment.id, Comment.content)
            .where(Comment.content.isnot(None), Comment.content != "")
            .order_by(Comment.id)
        )
        all_comments = result.all()

        # 3) 内存中聚合表情频率
        emote_freq: dict[str, int] = {}
        emote_comments: dict[str, set[int]] = {}
        emote_first: dict[str, datetime] = {}
        emote_last: dict[str, datetime] = {}
        comment_emote_data: list[dict] = []

        for comment_id, content in all_comments:
            emotes = extract_emotes(content)
            seen_in_comment: set[str] = set()
            for (name, position) in emotes:
                emote_freq[name] = emote_freq.get(name, 0) + 1
                if name not in emote_comments:
                    emote_comments[name] = set()
                emote_comments[name].add(comment_id)
                if name not in seen_in_comment:
                    seen_in_comment.add(name)
                comment_emote_data.append({
                    "comment_id": comment_id,
                    "emote_name": name,
                    "position": position,
                })

        if not emote_freq:
            logger.info("未发现任何表情 / No emotes found")
            return {"distinct_emotes": 0, "total_occurrences": 0}

        # 4) 插入 EmoteType
        sentiment_map = resources.emote_sentiment if resources.is_loaded else {}
        for name, freq in emote_freq.items():
            sentiment = sentiment_map.get(name, "neutral")
            stmt = (
                sqlite_insert(EmoteType)
                .values(
                    name=name,
                    frequency=freq,
                    sentiment=sentiment,
                    comment_count=len(emote_comments.get(name, set())),
                )
                .on_conflict_do_update(
                    index_elements=["name"],
                    set_={
                        "frequency": EmoteType.frequency + freq,
                        "comment_count": EmoteType.comment_count + len(emote_comments.get(name, set())),
                    },
                )
            )
            await self.db.execute(stmt)
        await self.db.flush()

        # 5) 获取 emote name -> id 映射
        result = await self.db.execute(select(EmoteType.id, EmoteType.name))
        name_to_id = {row[1]: row[0] for row in result.all()}

        # 6) 批量插入 CommentEmote
        for item in comment_emote_data:
            eid = name_to_id.get(item["emote_name"])
            if eid is None:
                continue
            stmt = (
                sqlite_insert(CommentEmote)
                .values(
                    comment_id=item["comment_id"],
                    emote_id=eid,
                    position=item["position"],
                )
                .on_conflict_do_nothing(index_elements=["comment_id", "emote_id", "position"])
            )
            await self.db.execute(stmt)
        await self.db.flush()

        total_occurrences = sum(emote_freq.values())
        logger.info(
            "表情提取完成: %d 种表情, %d 条引用 / Emote extraction done: %d types, %d occurrences",
            len(emote_freq), total_occurrences, len(emote_freq), total_occurrences,
        )
        return {
            "distinct_emotes": len(emote_freq),
            "total_occurrences": total_occurrences,
        }

    # ------------------------------------------------------------------
    # 查询接口
    # ------------------------------------------------------------------

    async def get_frequency_distribution(
        self,
        sort_by: str = "frequency",
        limit: int = 50,
        sentiment_filter: str | None = None,
    ) -> dict:
        """获取表情频率分布及情感统计。

        Args:
            sort_by: 排序方式 — frequency / comment_count
            limit: 返回数量 (1-200)
            sentiment_filter: 可选情感过滤 — positive / negative / neutral

        Returns:
            {"emotes": [...], "sentiment_breakdown": {...}, "total_distinct_emotes": int, "total_emote_occurrences": int}
        """
        # 总览统计
        total_result = await self.db.execute(
            select(
                func.count(EmoteType.id),
                func.sum(EmoteType.frequency),
                func.sum(EmoteType.comment_count),
            )
        )
        total_row = total_result.one()
        total_distinct = total_row[0] or 0
        total_occurrences = total_row[1] or 0

        # 情感分布
        sentiment_result = await self.db.execute(
            select(
                func.sum(case((EmoteType.sentiment == "positive", 1), else_=0)),
                func.sum(case((EmoteType.sentiment == "negative", 1), else_=0)),
                func.sum(case((EmoteType.sentiment == "neutral", 1), else_=0)),
            )
        )
        s_row = sentiment_result.one()
        pos_count = s_row[0] or 0
        neg_count = s_row[1] or 0
        neu_count = s_row[2] or 0
        s_total = pos_count + neg_count + neu_count

        # 频率排行
        order_col = EmoteType.comment_count if sort_by == "comment_count" else EmoteType.frequency
        query = select(EmoteType).order_by(order_col.desc()).limit(limit)
        if sentiment_filter and sentiment_filter != "all":
            query = query.where(EmoteType.sentiment == sentiment_filter)

        result = await self.db.execute(query)
        emote_rows = result.scalars().all()

        emotes = []
        for e in emote_rows:
            pct = round(e.frequency / total_occurrences * 100, 2) if total_occurrences else 0
            emotes.append({
                "name": e.name,
                "frequency": e.frequency,
                "comment_count": e.comment_count,
                "sentiment": e.sentiment,
                "percentage": pct,
            })

        return {
            "emotes": emotes,
            "sentiment_breakdown": {
                "positive": pos_count,
                "negative": neg_count,
                "neutral": neu_count,
                "total": s_total,
                "positive_pct": round(pos_count / s_total * 100, 1) if s_total else 0,
                "negative_pct": round(neg_count / s_total * 100, 1) if s_total else 0,
                "neutral_pct": round(neu_count / s_total * 100, 1) if s_total else 0,
            },
            "total_distinct_emotes": total_distinct,
            "total_emote_occurrences": total_occurrences,
        }

    async def get_emote_detail(self, emote_name: str) -> dict | None:
        """获取单个表情的详细信息，含评论样例和平均情感分。

        Args:
            emote_name: 表情名称（不含括号）

        Returns:
            表情详情 dict，不存在时返回 None
        """
        result = await self.db.execute(
            select(EmoteType).where(EmoteType.name == emote_name)
        )
        emote = result.scalar_one_or_none()
        if emote is None:
            return None

        # 获取包含该表情的评论样例（最多 5 条）
        sample_result = await self.db.execute(
            select(Comment.content)
            .join(CommentEmote, CommentEmote.comment_id == Comment.id)
            .where(CommentEmote.emote_id == emote.id)
            .limit(5)
        )
        sample_comments = [row[0] for row in sample_result.all()]

        # 计算包含该表情的评论的平均情感分
        avg_result = await self.db.execute(
            select(func.avg(SentimentResult.snownlp_score))
            .select_from(CommentEmote)
            .join(SentimentResult, SentimentResult.comment_id == CommentEmote.comment_id)
            .where(CommentEmote.emote_id == emote.id)
        )
        avg_score = avg_result.scalar()

        return {
            "name": emote.name,
            "frequency": emote.frequency,
            "comment_count": emote.comment_count,
            "sentiment": emote.sentiment,
            "sample_comments": sample_comments,
            "avg_text_sentiment": round(float(avg_score), 4) if avg_score is not None else None,
        }

    async def get_sentiment_correlation(self) -> list[dict]:
        """获取表情情感与文本情感的交叉分析。

        对于每种表情，计算包含该表情的评论的平均文本情感分，
        并与表情自身的情感标签对比，计算 sentiment_delta。

        Returns:
            list of correlation dicts，按 comment_count 降序
        """
        # 子查询：每种表情关联的评论情感平均分
        result = await self.db.execute(
            select(
                EmoteType.name,
                EmoteType.sentiment,
                func.avg(SentimentResult.snownlp_score),
                EmoteType.comment_count,
            )
            .join(CommentEmote, CommentEmote.emote_id == EmoteType.id)
            .join(SentimentResult, SentimentResult.comment_id == CommentEmote.comment_id)
            .group_by(EmoteType.id)
            .order_by(EmoteType.comment_count.desc())
            .limit(50)
        )
        rows = result.all()

        correlations = []
        for name, emote_sent, avg_score, count in rows:
            # 表情预期情感 → 文本分数映射（与 sentiment.py 阈值同步）
            expected = {
                "positive": POSITIVE_THRESHOLD,
                "negative": NEGATIVE_THRESHOLD,
                "neutral": (POSITIVE_THRESHOLD + NEGATIVE_THRESHOLD) / 2,
            }
            expected_score = expected.get(emote_sent, 0.5)
            delta = round(float(avg_score) - expected_score, 4) if avg_score is not None else 0

            correlations.append({
                "emote_name": name,
                "emote_sentiment": emote_sent,
                "avg_text_sentiment": round(float(avg_score), 4) if avg_score is not None else 0,
                "comment_count": count,
                "sentiment_delta": delta,
            })

        return correlations

    async def get_emote_timeline(
        self, emote_name: str, granularity: str = "month"
    ) -> list[dict]:
        """获取指定表情的时间趋势。

        Args:
            emote_name: 表情名称
            granularity: 聚合粒度 — month / week

        Returns:
            list of {"period": str, "frequency": int}
        """
        # 先获取 emote_id
        result = await self.db.execute(
            select(EmoteType.id).where(EmoteType.name == emote_name)
        )
        emote_id = result.scalar()
        if emote_id is None:
            return []

        # 时间聚合（SQLite strftime）
        if granularity == "week":
            period_fmt = "%Y-%W"
        else:
            period_fmt = "%Y-%m"

        query = (
            select(
                func.strftime(period_fmt, Comment.create_datetime).label("period"),
                func.count(CommentEmote.id).label("cnt"),
            )
            .select_from(CommentEmote)
            .join(Comment, Comment.id == CommentEmote.comment_id)
            .where(
                CommentEmote.emote_id == emote_id,
                Comment.create_datetime.isnot(None),
            )
            .group_by("period")
            .order_by("period")
        )
        result = await self.db.execute(query)
        rows = result.all()

        return [{"period": row[0], "frequency": row[1]} for row in rows]

    async def get_wordcloud_data(self, limit: int = 100) -> list[dict]:
        """获取表情词云数据（兼容 WordCloudChart 的 name/value 格式）。

        Args:
            limit: 返回数量

        Returns:
            list of {"name": str, "value": int}
        """
        result = await self.db.execute(
            select(EmoteType.name, EmoteType.frequency)
            .order_by(EmoteType.frequency.desc())
            .limit(limit)
        )
        rows = result.all()
        return [{"name": row[0], "value": row[1]} for row in rows]
