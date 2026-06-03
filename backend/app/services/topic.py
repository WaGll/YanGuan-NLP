"""
主题建模服务

提供 LDA 主题建模（Gensim）、BERTopic 存根，以及主题-文档分配的持久化。
"""

import json
import logging
from collections import Counter, defaultdict
from typing import Any

import numpy as np
from gensim.corpora import Dictionary
from gensim.models import CoherenceModel, LdaModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.models.topic import DocTopic, Topic, TopicKeyword

logger = logging.getLogger(__name__)


class TopicService:
    """主题建模服务。

    基于评论分词数据，使用 Gensim LDA 进行主题建模，
    自动选择最佳主题数 k，持久化主题、关键词和文档分配。
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # 公开方法
    # ------------------------------------------------------------------

    async def run_lda(self, min_k: int = 2, max_k: int = 6) -> int:
        """运行 LDA 主题建模，自动选择最佳 k。

        步骤:
        1. 加载所有评论的 tokens_json
        2. 构建 Gensim 词典和语料库
        3. 对 [min_k, max_k] 范围内的 k 训练 LDA，计算一致性分数
        4. 选择一致性最高的 k 作为最佳主题数
        5. 持久化主题、主题关键词、文档-主题分配

        Args:
            min_k: 最小主题数
            max_k: 最大主题数

        Returns:
            最佳 k 值
        """
        # 1. 加载分词数据
        result = await self.db.execute(
            select(Comment.id, Comment.tokens_json).where(
                Comment.tokens_json.isnot(None),
                Comment.token_count > 0,
            )
        )
        rows = result.all()
        if not rows:
            logger.warning("无可用分词数据，无法运行 LDA")
            return 0

        texts: list[list[str]] = []
        comment_ids: list[int] = []
        for comment_id, tokens_json in rows:
            try:
                tokens = json.loads(tokens_json)
                if tokens:
                    texts.append(tokens)
                    comment_ids.append(comment_id)
            except json.JSONDecodeError:
                continue

        if len(texts) < 10:
            logger.warning("有效文档数不足 %d 篇，无法运行 LDA", len(texts))
            return 0

        # 2. 构建词典和语料库
        dictionary = Dictionary(texts)
        # 过滤极端词频
        dictionary.filter_extremes(no_below=2, no_above=0.8)
        corpus = [dictionary.doc2bow(text) for text in texts]

        # 3. 训练多个 k 的 LDA 模型，计算一致性
        best_k = min_k
        best_coherence = -1.0
        best_model = None
        best_corpus_topics = None

        for k in range(min_k, max_k + 1):
            try:
                lda = LdaModel(
                    corpus=corpus,
                    id2word=dictionary,
                    num_topics=k,
                    random_state=42,
                    passes=10,
                    alpha="auto",
                    eta="auto",
                )
                coherence_model = CoherenceModel(
                    model=lda,
                    texts=texts,
                    dictionary=dictionary,
                    coherence="c_v",
                )
                coherence = coherence_model.get_coherence()
                logger.info("k=%d, coherence=%.4f", k, coherence)

                if coherence > best_coherence:
                    best_coherence = coherence
                    best_k = k
                    best_model = lda
                    # 获取每个文档的主题分布
                    best_corpus_topics = [
                        lda.get_document_topics(doc, minimum_probability=0.01)
                        for doc in corpus
                    ]
            except Exception as e:
                logger.error("k=%d 训练失败: %s", k, e)
                continue

        if best_model is None:
            logger.warning("所有 k 的 LDA 模型训练均失败")
            return 0

        logger.info("最佳主题数 k=%d, coherence=%.4f", best_k, best_coherence)

        # 4. 清除旧的 LDA 数据
        await self._clear_old_lda_data()

        # 5. 持久化主题
        topic_map = {}  # topic_index -> Topic ORM 对象
        for topic_idx in range(best_k):
            topic = Topic(
                method="lda",
                topic_index=topic_idx,
                label=f"主题 {topic_idx + 1}",
                coherence_score=best_coherence,
            )
            self.db.add(topic)
            await self.db.flush()  # 获取 id
            topic_map[topic_idx] = topic

        # 6. 持久化主题关键词（前 10 个）
        for topic_idx in range(best_k):
            top_words = best_model.show_topic(topic_idx, topn=10)
            for rank, (word, weight) in enumerate(top_words, start=1):
                self.db.add(
                    TopicKeyword(
                        topic_id=topic_map[topic_idx].id,
                        word=word,
                        weight=float(weight),
                        rank=rank,
                    )
                )

        # 7. 持久化文档-主题分配
        assert best_corpus_topics is not None
        for doc_idx, doc_topics in enumerate(best_corpus_topics):
            if not doc_topics:
                continue
            comment_id = comment_ids[doc_idx]
            # 找到主导主题
            dominant_topic_idx, dominant_prob = max(doc_topics, key=lambda x: x[1])
            for topic_idx, prob in doc_topics:
                self.db.add(
                    DocTopic(
                        comment_id=comment_id,
                        topic_id=topic_map[topic_idx].id,
                        probability=float(prob),
                        is_primary=(topic_idx == dominant_topic_idx),
                    )
                )

        await self.db.commit()
        logger.info("LDA 主题建模完成，k=%d，已持久化 %d 个主题", best_k, best_k)
        return best_k

    async def run_bertopic(self) -> None:
        """BERTopic 主题建模（尚未实现）。

        当前仅记录日志，保留为未来扩展接口。
        """
        logger.info("BERTopic not yet implemented")

    async def get_topics(self, method: str = "lda") -> list[dict[str, Any]]:
        """获取指定方法的所有主题及关键词。

        Args:
            method: 主题建模方法（lda / bertopic / hdbscan）

        Returns:
            [{topic_id, topic_index, label, coherence_score,
              keywords: [{word, weight, rank}, ...], doc_count: int}, ...]
        """
        # 查询主题
        result = await self.db.execute(
            select(Topic).where(Topic.method == method).order_by(Topic.topic_index)
        )
        topics = result.scalars().all()

        output = []
        for topic in topics:
            # 查询该主题下的关键词
            kw_result = await self.db.execute(
                select(TopicKeyword)
                .where(TopicKeyword.topic_id == topic.id)
                .order_by(TopicKeyword.rank)
            )
            keywords = kw_result.scalars().all()

            # 查询分配到该主题的文档数
            doc_count_result = await self.db.execute(
                select(DocTopic).where(
                    DocTopic.topic_id == topic.id, DocTopic.is_primary.is_(True)
                )
            )
            doc_count = len(doc_count_result.scalars().all())

            output.append({
                "topic_id": topic.id,
                "topic_index": topic.topic_index,
                "label": topic.label or f"主题 {topic.topic_index + 1}",
                "coherence_score": round(topic.coherence_score, 4) if topic.coherence_score else None,
                "keywords": [
                    {"word": kw.word, "weight": round(kw.weight, 4), "rank": kw.rank}
                    for kw in keywords
                ],
                "doc_count": doc_count,
            })

        return output

    # ------------------------------------------------------------------
    # 私有方法
    # ------------------------------------------------------------------

    async def _clear_old_lda_data(self) -> None:
        """清除旧的 LDA 数据（主题、关键词、文档分配）。"""
        # 先查旧 LDA 主题 id
        result = await self.db.execute(
            select(Topic.id).where(Topic.method == "lda")
        )
        old_ids = [row[0] for row in result.all()]
        if old_ids:
            await self.db.execute(
                delete(DocTopic).where(DocTopic.topic_id.in_(old_ids))
            )
            await self.db.execute(
                delete(TopicKeyword).where(TopicKeyword.topic_id.in_(old_ids))
            )
            await self.db.execute(
                delete(Topic).where(Topic.id.in_(old_ids))
            )
            await self.db.flush()
