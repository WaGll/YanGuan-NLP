"""
关键词分析服务

提供词频统计、TF-IDF 提取和词云数据生成。
"""

import json
import logging
from collections import Counter
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.models.keyword import Keyword

logger = logging.getLogger(__name__)


class KeywordService:
    """关键词分析服务。

    提供词频统计、TF-IDF 计算和词云数据生成。
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def compute_frequencies(self) -> int:
        """统计所有评论的 Token 词频并持久化到 keywords 表。

        Returns:
            提取的关键词数量
        """
        result = await self.db.execute(
            select(Comment.tokens_json).where(
                Comment.tokens_json.isnot(None),
                Comment.token_count > 0,
            )
        )
        rows = result.all()

        # 统计词频
        counter: Counter = Counter()
        for (tokens_json,) in rows:
            try:
                tokens = json.loads(tokens_json)
                counter.update(tokens)
            except json.JSONDecodeError:
                continue

        # 批量写入
        total = 0
        for word, freq in counter.most_common():
            self.db.add(
                Keyword(
                    word=word,
                    frequency=freq,
                )
            )
            total += 1

        await self.db.commit()
        logger.info(f"词频统计完成，共 {total} 个关键词")
        return total

    async def compute_tfidf(self) -> list[dict[str, Any]]:
        """使用 TF-IDF 提取每个评论中最重要的词。

        Returns:
            [{word, frequency, tfidf_score}, ...]
        """
        # 获取所有评论的 tokens
        result = await self.db.execute(
            select(Comment.tokens_json).where(
                Comment.tokens_json.isnot(None),
                Comment.token_count > 0,
            )
        )
        rows = result.all()

        documents = []
        for (tokens_json,) in rows:
            try:
                tokens = json.loads(tokens_json)
                documents.append(" ".join(tokens))
            except json.JSONDecodeError:
                continue

        if not documents:
            return []

        # TF-IDF
        vectorizer = TfidfVectorizer(max_features=500)
        tfidf_matrix = vectorizer.fit_transform(documents)

        # 汇总每个词的 TF-IDF 分数
        feature_names = vectorizer.get_feature_names_out()
        tfidf_scores = tfidf_matrix.sum(axis=0).A1  # 所有文档汇总

        results = []
        for word, score in zip(feature_names, tfidf_scores):
            # 更新 keywords 表的 tfidf_score
            await self.db.execute(
                text("UPDATE keywords SET tfidf_score = :score WHERE word = :word"),
                {"score": float(score), "word": word},
            )
            results.append({
                "word": word,
                "tfidf_score": round(float(score), 4),
            })

        await self.db.commit()
        return sorted(results, key=lambda x: x["tfidf_score"], reverse=True)

    async def get_keywords(
        self, sort_by: str = "frequency", limit: int = 50, min_frequency: int = 1
    ) -> list[dict[str, Any]]:
        """获取关键词列表。

        Args:
            sort_by: 排序方式 (frequency / tfidf)
            limit: 返回数量
            min_frequency: 最小词频过滤

        Returns:
            [{word, frequency, tfidf_score}, ...]
        """
        order_col = Keyword.tfidf_score if sort_by == "tfidf" else Keyword.frequency

        result = await self.db.execute(
            select(Keyword.word, Keyword.frequency, Keyword.tfidf_score)
            .where(Keyword.frequency >= min_frequency)
            .order_by(order_col.desc())
            .limit(limit)
        )

        return [
            {
                "word": row[0],
                "frequency": row[1],
                "tfidf_score": round(row[2], 4) if row[2] else None,
            }
            for row in result.all()
        ]

    async def get_wordcloud_data(self, limit: int = 200) -> list[dict[str, int]]:
        """生成词云数据（前端渲染）。

        Args:
            limit: 返回词数

        Returns:
            [{name: str, value: int}, ...]
        """
        result = await self.db.execute(
            select(Keyword.word, Keyword.frequency)
            .order_by(Keyword.frequency.desc())
            .limit(limit)
        )
        return [{"name": row[0], "value": row[1]} for row in result.all()]
