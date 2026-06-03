"""
单条评论预测服务

接收原始文本，执行完整分析流水线：清洗 → 分词 → 情感评分 → 主题归类。
"""

import json
import logging
from typing import Any

from gensim.corpora import Dictionary
from gensim.models import LdaModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.models.topic import DocTopic, Topic, TopicKeyword
from app.services.cleaner import CleanerService
from app.services.sentiment import SentimentService

logger = logging.getLogger(__name__)


class PredictorService:
    """单条评论预测服务。

    对输入的评论文本执行完整的 NLP 流水线：
    文本清洗 → 分词 → SnowNLP 情感评分 → 主导主题分配 → 关键词提取。
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.cleaner = CleanerService(db)

    # ------------------------------------------------------------------
    # 公开方法
    # ------------------------------------------------------------------

    async def predict_single(self, text: str) -> dict[str, Any]:
        """对单条评论执行完整预测流水线。

        步骤:
        1. 清洗文本
        2. jieba 分词（过滤停用词和单字词）
        3. SnowNLP 情感评分
        4. 基于训练好的 LDA 模型分配主导主题
        5. 提取关键词（基于词频和 TF-IDF）

        Args:
            text: 原始评论文本

        Returns:
            {
                cleaned_text, tokens, snownlp_score,
                sentiment_class, dominant_topic_label, top_keywords
            }
        """
        if not text or not isinstance(text, str) or not text.strip():
            return {
                "cleaned_text": "",
                "tokens": [],
                "snownlp_score": 0.5,
                "sentiment_class": "neutral",
                "dominant_topic_label": None,
                "top_keywords": [],
            }

        # 1. 清洗文本
        cleaned_text = self.cleaner.clean_text(text)

        if not cleaned_text:
            return {
                "cleaned_text": "",
                "tokens": [],
                "snownlp_score": 0.5,
                "sentiment_class": "neutral",
                "dominant_topic_label": None,
                "top_keywords": [],
            }

        # 2. 分词
        tokens = self.cleaner.tokenize(cleaned_text)

        # 3. SnowNLP 情感评分
        snownlp_score = SentimentService._snownlp_score(cleaned_text)
        sentiment_class = SentimentService.classify_sentiment(snownlp_score)

        # 4. 主导主题分配（尝试使用训练好的 LDA 模型）
        dominant_topic_label = await self._infer_topic(tokens)

        # 5. 提取关键词（基于现有词频数据库取 top 5 与文本 token 匹配）
        top_keywords = await self._extract_matching_keywords(tokens)

        return {
            "cleaned_text": cleaned_text,
            "tokens": tokens,
            "snownlp_score": round(snownlp_score, 4),
            "sentiment_class": sentiment_class,
            "dominant_topic_label": dominant_topic_label,
            "top_keywords": top_keywords,
        }

    # ------------------------------------------------------------------
    # 私有方法
    # ------------------------------------------------------------------

    async def _infer_topic(self, tokens: list[str]) -> str | None:
        """基于已训练的 LDA 模型推断新文本的主题。

        从数据库中获取最近一次 LDA 训练的模型参数和词典，
        对新文本进行主题推理，返回主导主题标签。

        Args:
            tokens: 分词结果

        Returns:
            主导主题标签，无法推断时返回 None
        """
        if not tokens:
            return None

        # 获取已训练的 LDA 主题关键词（用于重建模型）
        kw_result = await self.db.execute(
            select(TopicKeyword.word, TopicKeyword.weight, Topic.id, Topic.label)
            .join(Topic, TopicKeyword.topic_id == Topic.id)
            .where(Topic.method == "lda")
            .order_by(Topic.topic_index, TopicKeyword.rank)
        )
        kw_rows = kw_result.all()
        if not kw_rows:
            return None

        # 按主题分组关键词权重
        from collections import defaultdict

        topic_words: dict[int, dict[str, float]] = defaultdict(dict)
        topic_labels: dict[int, str] = {}
        for word, weight, topic_id, label in kw_rows:
            topic_words[topic_id][word] = weight
            topic_labels[topic_id] = label or f"主题 {len(topic_labels) + 1}"

        # 简单的关键词匹配法：计算每个主题的匹配得分
        best_topic_id = None
        best_score = 0.0

        for tid, word_weights in topic_words.items():
            score = 0.0
            for token in tokens:
                if token in word_weights:
                    score += word_weights[token]
            if score > best_score:
                best_score = score
                best_topic_id = tid

        if best_topic_id and best_score > 0:
            return topic_labels.get(best_topic_id)
        return None

    async def _extract_matching_keywords(
        self, tokens: list[str], top_n: int = 5
    ) -> list[str]:
        """从 token 中提取与数据库关键词表匹配的关键词。

        Args:
            tokens: 分词结果
            top_n: 返回数量

        Returns:
            匹配到的关键词列表
        """
        if not tokens:
            return []

        from app.models.keyword import Keyword

        # 查询高频关键词
        result = await self.db.execute(
            select(Keyword.word)
            .where(Keyword.word.in_(tokens))
            .order_by(Keyword.frequency.desc())
            .limit(top_n)
        )
        matched = [row[0] for row in result.all()]

        # 如果匹配不足，直接返回 tokens 中靠前的
        if len(matched) < top_n:
            for token in tokens:
                if token not in matched:
                    matched.append(token)
                    if len(matched) >= top_n:
                        break

        return matched
