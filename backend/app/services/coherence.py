"""
双轨 Coherence 评估服务

提供 LDA vs BERTopic 一致性对比、逐评论 coherence 评估、
混合主题检测等分析功能。
"""

import json
import logging
import statistics
from typing import Any

import numpy as np
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.models.topic import DocTopic, Topic, TopicKeyword

logger = logging.getLogger(__name__)


def _quality_tier(coherence: float) -> str:
    """将 coherence 分数映射到质量分级。"""
    if coherence >= 0.5:
        return "excellent"
    elif coherence >= 0.4:
        return "good"
    elif coherence >= 0.3:
        return "fair"
    return "poor"


class CoherenceService:
    """双轨 Coherence 评估服务。

    用法:
        async with AsyncSession(...) as db:
            service = CoherenceService(db)
            comparison = await service.compare_methods()
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # 双轨对比
    # ------------------------------------------------------------------

    async def compare_methods(self) -> dict[str, Any]:
        """对比 LDA 和 BERTopic 的 coherence 指标。

        Returns:
            dict，包含 methods, winner, margin, recommendation
        """
        methods = ["lda", "bertopic"]
        result_methods: list[dict] = []

        for method in methods:
            metrics = await self._compute_method_metrics(method)
            if metrics and metrics["num_topics"] > 0:
                result_methods.append(metrics)

        if not result_methods:
            return {
                "methods": [],
                "winner": None,
                "margin": 0.0,
                "recommendation": "暂无主题数据，请先运行主题建模管道。",
            }

        if len(result_methods) == 1:
            m = result_methods[0]
            return {
                "methods": result_methods,
                "winner": m["method"],
                "margin": 0.0,
                "recommendation": f"仅 {m['method'].upper()} 有数据。建议同时运行两种方法以获得对比。",
            }

        # 双方法对比
        m0, m1 = result_methods[0], result_methods[1]
        margin = abs(m0["avg_coherence"] - m1["avg_coherence"])
        if m0["avg_coherence"] > m1["avg_coherence"]:
            winner = m0["method"]
            loser = m1["method"]
        elif m1["avg_coherence"] > m0["avg_coherence"]:
            winner = m1["method"]
            loser = m0["method"]
        else:
            winner = "tie"
            loser = ""

        if winner == "tie":
            recommendation = "两种方法 coherence 相当，均可使用。"
        else:
            diff = m0["avg_coherence"] - m1["avg_coherence"]
            abs_diff = abs(diff)
            if abs_diff < 0.05:
                recommendation = (
                    f"{winner.upper()} 略优于 {loser.upper()}，差距较小 (Δ={abs_diff:.3f})，"
                    f"两种方法均可选用。"
                )
            elif abs_diff < 0.10:
                recommendation = (
                    f"推荐使用 {winner.upper()}，coherence 高出 {loser.upper()} "
                    f"约 {abs_diff:.3f}。"
                )
            else:
                recommendation = (
                    f"强烈推荐 {winner.upper()}，coherence 显著优于 {loser.upper()} "
                    f"(Δ={abs_diff:.3f})。"
                )

        return {
            "methods": result_methods,
            "winner": winner,
            "margin": round(margin, 4),
            "recommendation": recommendation,
        }

    async def _compute_method_metrics(self, method: str) -> dict | None:
        """计算单个方法的主题 coherence 统计。

        从 Topic 表读取已持久化的 coherence_score。
        """
        result = await self.db.execute(
            select(
                Topic.id,
                Topic.topic_index,
                Topic.label,
                Topic.business_label,
                Topic.coherence_score,
            ).where(
                Topic.method == method,
                Topic.topic_index >= 0,  # 排除 outlier
            ).order_by(Topic.coherence_score.desc())
        )
        rows = result.all()

        if not rows:
            return None

        scores = [row[4] for row in rows if row[4] is not None]
        if not scores:
            return None

        topic_scores = [
            {
                "topic_index": row[1],
                "label": row[2],
                "business_label": row[3],
                "coherence_score": row[4],
                "quality_tier": _quality_tier(row[4]),
            }
            for row in rows
        ]

        return {
            "method": method,
            "num_topics": len(topic_scores),
            "avg_coherence": round(float(np.mean(scores)), 4),
            "min_coherence": round(float(min(scores)), 4),
            "max_coherence": round(float(max(scores)), 4),
            "std_coherence": round(float(statistics.stdev(scores)) if len(scores) > 1 else 0.0, 4),
            "topic_scores": topic_scores,
        }

    # ------------------------------------------------------------------
    # 逐评论 Coherence
    # ------------------------------------------------------------------

    async def get_per_comment_coherence(
        self, comment_id: int, method: str = "lda"
    ) -> dict | None:
        """获取单条评论与主题的匹配度。

        Args:
            comment_id: 评论 ID
            method: 主题建模方法

        Returns:
            dict 或 None（评论无主题分配时）
        """
        # 查询评论的主题分配
        result = await self.db.execute(
            select(
                DocTopic,
                Topic.business_label,
                Topic.topic_index,
            )
            .join(Topic, DocTopic.topic_id == Topic.id)
            .where(
                DocTopic.comment_id == comment_id,
                Topic.method == method,
                Topic.topic_index >= 0,
            )
            .order_by(DocTopic.probability.desc())
        )
        rows = result.all()

        if not rows:
            return None

        # 取主主题和次主题
        primary = rows[0] if rows else None
        secondary = rows[1] if len(rows) > 1 else None

        # 获取评论内容
        comment_result = await self.db.execute(
            select(Comment.cleaned_content).where(Comment.id == comment_id)
        )
        comment_row = comment_result.one_or_none()
        content = comment_row[0] if comment_row else ""
        if content and len(content) > 200:
            content = content[:200] + "..."

        # 计算 coherence_score：用 primary probability 作为匹配度的代理
        # 同时考虑主次主题的 gap
        primary_prob = float(primary[0].probability) if primary else None
        secondary_prob = float(secondary[0].probability) if secondary else None

        if primary_prob is not None:
            if secondary_prob is not None:
                coherence_score = round(primary_prob * (1.0 - secondary_prob), 4)
            else:
                coherence_score = primary_prob
        else:
            coherence_score = None

        is_mixed = (
            secondary_prob is not None
            and primary_prob is not None
            and secondary_prob >= 0.30
            and primary_prob < 0.50
        )

        return {
            "comment_id": comment_id,
            "content": content or "",
            "primary_topic_id": primary[0].topic_id if primary else None,
            "primary_topic_label": primary[1] if primary else None,
            "primary_probability": primary_prob,
            "secondary_topic_id": secondary[0].topic_id if secondary else None,
            "secondary_topic_label": secondary[1] if secondary else None,
            "secondary_probability": secondary_prob,
            "coherence_score": coherence_score,
            "is_mixed": is_mixed,
        }

    async def get_all_per_comment_coherence(
        self, method: str = "lda", page: int = 1, page_size: int = 50,
    ) -> dict:
        """批量获取逐评论 coherence（分页）。

        Args:
            method: 主题建模方法
            page: 页码
            page_size: 每页数量

        Returns:
            dict，包含 items, total, page, page_size
        """
        # 获取有主题分配的评论数
        from sqlalchemy import and_
        count_query = select(func.count(func.distinct(DocTopic.comment_id))).where(
            DocTopic.topic.has(
                and_(Topic.method == method, Topic.topic_index >= 0)
            )
        )
        result = await self.db.execute(count_query)
        total = result.scalar() or 0

        if total == 0:
            return {"items": [], "total": 0, "page": page, "page_size": page_size}

        # 分页查询评论 ID
        id_query = (
            select(
                DocTopic.comment_id,
                func.max(case((DocTopic.is_primary, DocTopic.probability), else_=0)).label("max_prob"),
            )
            .join(Topic, DocTopic.topic_id == Topic.id)
            .where(Topic.method == method, Topic.topic_index >= 0)
            .group_by(DocTopic.comment_id)
            .order_by(func.max(case((DocTopic.is_primary, DocTopic.probability), else_=0)).desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(id_query)
        comment_ids = [row[0] for row in result.all()]

        # 逐个获取详情
        items = []
        for cid in comment_ids:
            detail = await self.get_per_comment_coherence(cid, method)
            if detail:
                items.append(detail)

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ------------------------------------------------------------------
    # 混合主题检测
    # ------------------------------------------------------------------

    async def detect_mixed_topics(
        self, threshold: float = 0.30, method: str = "lda", limit: int = 100,
    ) -> list[dict]:
        """检测同时属于多个主题的评论（混合主题）。

        条件:
        - 次主题概率 ≥ threshold
        - 主主题概率 < 0.50（真正模糊）

        Args:
            threshold: 次主题概率阈值
            method: 主题建模方法
            limit: 最大返回数

        Returns:
            list[dict]，按 gap 升序（最混合的在前）
        """
        # 查询 DocTopic，按 comment_id 分组，取每组的 top-2 主题概率
        result = await self.db.execute(
            select(
                DocTopic.comment_id,
                DocTopic.topic_id,
                Topic.business_label,
                DocTopic.probability,
                DocTopic.is_primary,
            )
            .join(Topic, DocTopic.topic_id == Topic.id)
            .where(Topic.method == method, Topic.topic_index >= 0)
            .order_by(DocTopic.comment_id, DocTopic.probability.desc())
        )
        rows = result.all()

        # 按 comment_id 分组
        from collections import defaultdict
        groups: dict[int, list] = defaultdict(list)
        for row in rows:
            groups[row[0]].append({
                "topic_id": row[1],
                "business_label": row[2],
                "probability": float(row[3]),
                "is_primary": row[4],
            })

        # 检测混合主题
        mixed = []
        for comment_id, assignments in groups.items():
            if len(assignments) < 2:
                continue
            primary = assignments[0]
            secondary = assignments[1]

            if (
                secondary["probability"] >= threshold
                and primary["probability"] < 0.50
            ):
                mixed.append({
                    "comment_id": comment_id,
                    "primary_topic": primary["business_label"],
                    "primary_prob": primary["probability"],
                    "secondary_topic": secondary["business_label"],
                    "secondary_prob": secondary["probability"],
                    "gap": round(primary["probability"] - secondary["probability"], 4),
                })

        # 按 gap 升序排序（最混合的在前）
        mixed.sort(key=lambda x: x["gap"])
        mixed = mixed[:limit]

        # 补充评论内容
        if mixed:
            cids = [m["comment_id"] for m in mixed]
            result = await self.db.execute(
                select(Comment.id, Comment.cleaned_content).where(
                    Comment.id.in_(cids)
                )
            )
            content_map = {row[0]: row[1] for row in result.all()}
            for item in mixed:
                content = content_map.get(item["comment_id"], "")
                item["content"] = content[:200] + "..." if content and len(content) > 200 else (content or "")

        return mixed

    # ------------------------------------------------------------------
    # Dashboard 摘要
    # ------------------------------------------------------------------

    async def get_summary(self) -> dict:
        """获取 Dashboard coherence 摘要。

        Returns:
            dict，包含 lda, bertopic, mixed_topic_count, mixed_topic_pct, total_comments_with_topics
        """
        lda_metrics = await self._compute_method_metrics("lda")
        bertopic_metrics = await self._compute_method_metrics("bertopic")

        # 获取有主题分配的评论总数
        result = await self.db.execute(
            select(func.count(func.distinct(DocTopic.comment_id)))
        )
        total_with_topics = result.scalar() or 0

        # 混合主题（LDA 为主）
        mixed = await self.detect_mixed_topics(method="lda", limit=100)
        mixed_count = len(mixed)

        return {
            "lda": lda_metrics,
            "bertopic": bertopic_metrics,
            "mixed_topic_count": mixed_count,
            "mixed_topic_pct": round(mixed_count / total_with_topics * 100, 1) if total_with_topics > 0 else 0.0,
            "total_comments_with_topics": total_with_topics,
        }
