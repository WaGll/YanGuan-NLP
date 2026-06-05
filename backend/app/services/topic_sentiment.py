"""
主题-情感联合分析服务

交叉分析 LDA 主题分配与情感分类，生成可用于热力图的联合矩阵。
"""

import logging
from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sentiment import SentimentResult
from app.models.topic import DocTopic, Topic

logger = logging.getLogger(__name__)


class TopicSentimentService:
    """主题-情感联合分析服务。

    将每个文档的主导主题与情感分类进行交叉制表，
    生成供前端热力图使用的矩阵数据。
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # 公开方法
    # ------------------------------------------------------------------

    async def compute_joint_matrix(self, method: str = "lda") -> dict[str, Any]:
        """计算主题-情感联合分布矩阵。

        步骤:
        1. 查询指定方法下所有 doc_topic（仅主导主题）
        2. 关联 sentiment_results 获取情感分类
        3. 交叉制表，计算每个 (topic, sentiment) 单元格的 count 和 proportion

        Args:
            method: 主题建模方法（lda / bertopic / hdbscan）

        Returns:
            {
                topics: [str],                    # 主题标签列表
                sentiment_classes: [str],         # 情感类别列表
                cells: [[{                         # 二维矩阵单元格
                    topic_id, topic_label,
                    sentiment_class, count, proportion
                }]]
            }
        """
        # 1. 查询主题列表
        topic_result = await self.db.execute(
            select(Topic.id, Topic.topic_index, Topic.label, Topic.business_label).where(
                Topic.method == method
            ).order_by(Topic.topic_index)
        )
        topic_rows = topic_result.all()
        if not topic_rows:
            logger.warning("未找到 method=%s 的主题数据", method)
            return {"topics": [], "topic_business_labels": [], "sentiment_classes": [], "cells": []}

        topic_map = {tid: (tidx, tlabel or f"主题 {tidx + 1}", blabel or tlabel or f"主题 {tidx + 1}")
                     for tid, tidx, tlabel, blabel in topic_rows}

        # 2. 查询主导主题分配 + 情感分类
        result = await self.db.execute(
            select(
                DocTopic.topic_id,
                SentimentResult.sentiment_class,
            )
            .join(SentimentResult, DocTopic.comment_id == SentimentResult.comment_id)
            .where(
                DocTopic.topic_id.in_(list(topic_map.keys())),
                DocTopic.is_primary.is_(True),
            )
        )
        rows = result.all()

        if not rows:
            logger.warning("无主题-情感联合数据")
            return {"topics": [], "sentiment_classes": [], "cells": []}

        # 3. 交叉制表
        # 格子计数: (topic_id, sentiment_class) -> count
        cell_counts: dict[tuple[int, str], int] = defaultdict(int)
        for topic_id, sentiment_class in rows:
            cell_counts[(topic_id, sentiment_class)] += 1

        # 收集所有出现的情感类别
        sentiment_classes = sorted(set(sc for _, sc in cell_counts.keys()))
        if not sentiment_classes:
            sentiment_classes = ["positive", "neutral", "negative"]

        # 按 topic_index 排序的主题 id 列表
        sorted_topic_ids = sorted(topic_map.keys(), key=lambda tid: topic_map[tid][0])
        topic_labels = [topic_map[tid][1] for tid in sorted_topic_ids]
        topic_business_labels = [topic_map[tid][2] for tid in sorted_topic_ids]

        # 计算每个主题的总文档数
        topic_totals: dict[int, int] = defaultdict(int)
        for (tid, _), count in cell_counts.items():
            topic_totals[tid] += count

        # 4. 构建矩阵 cells
        cells: list[list[dict[str, Any]]] = []
        for topic_id in sorted_topic_ids:
            row_cells = []
            topic_total = topic_totals.get(topic_id, 1)
            for sc in sentiment_classes:
                count = cell_counts.get((topic_id, sc), 0)
                proportion = round(count / topic_total, 4) if topic_total > 0 else 0.0
                row_cells.append({
                    "topic_id": topic_id,
                    "topic": topic_map[topic_id][1],
                    "topic_index": topic_map[topic_id][0],
                    "sentiment": sc,
                    "count": count,
                    "proportion": proportion,
                })
            cells.append(row_cells)

        logger.info(
            "主题-情感联合矩阵生成: %d 主题 x %d 情感类别",
            len(topic_labels),
            len(sentiment_classes),
        )
        return {
            "topics": topic_labels,
            "topic_business_labels": topic_business_labels,
            "sentiment_classes": sentiment_classes,
            "cells": cells,
        }
