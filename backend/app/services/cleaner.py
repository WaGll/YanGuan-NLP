"""
文本清洗与分词服务

整合原 data_cleaner.py 的核心逻辑，修复了中文 \\b 正则 bug。
作为无状态服务，支持批量处理和单条处理。
"""

import json
import logging
from pathlib import Path
from typing import Optional

import jieba
from gensim.models.phrases import Phrases
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.utils.chinese import clean_chinese_text
from app.utils.resources import NLPResources

logger = logging.getLogger(__name__)


class CleanerService:
    """文本清洗与分词服务。

    依赖 NLPResources 单例获取停用词和同义词，
    对评论执行清洗 → 分词 → 同义词替换 → Bigram 短语挖掘。
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.resources = NLPResources.get_instance()

        if not self.resources.is_loaded:
            raise RuntimeError(
                "NLPResources 尚未加载，请先调用 NLPResources.get_instance().load(data_dir)"
            )

    def clean_text(self, text: str) -> str:
        """清洗单条评论文本。

        Args:
            text: 原始评论文本

        Returns:
            清洗后的文本
        """
        return clean_chinese_text(text)

    def tokenize(self, text: str) -> list[str]:
        """对清洗后的文本进行分词。

        步骤: jieba 分词 → 过滤停用词 → 过滤单字词 → 同义词替换

        Args:
            text: 清洗后的文本

        Returns:
            分词结果列表
        """
        if not text:
            return []

        tokens = jieba.lcut(text)
        # 过滤停用词和单字词
        tokens = [
            w for w in tokens
            if w not in self.resources.stopwords and len(w) > 1
        ]
        # 同义词替换
        tokens = self.resources.replace_synonyms(tokens)
        return tokens

    def build_bigrams(self, tokens_list: list[list[str]]) -> list[list[str]]:
        """使用 Gensim Phrases 构建 Bigram 短语。

        Args:
            tokens_list: 多条评论的分词结果

        Returns:
            Bigram 短语替换后的分词结果
        """
        if not tokens_list:
            return []

        bigram_model = Phrases(tokens_list, min_count=20, threshold=50)
        return [
            [word.replace("_", " ") for word in bigram_model[doc]]
            for doc in tokens_list
        ]

    async def process_all(self, batch_size: int = 500) -> int:
        """批量处理数据库中所有未处理的评论。

        读取所有评论 → 清洗 → 分词 → Bigram → 更新数据库。

        Args:
            batch_size: 每批处理数量

        Returns:
            处理的评论总数
        """
        total_processed = 0

        while True:
            # 分批查询未处理的评论
            result = await self.db.execute(
                select(Comment.id, Comment.content)
                .where(
                    Comment.content.isnot(None),
                    Comment.cleaned_content.is_(None),
                )
                .limit(batch_size)
            )
            rows = result.all()
            if not rows:
                break

            # 收集所有文本用于分词
            comment_ids: list[int] = []
            cleaned_texts: list[str] = []
            all_tokens: list[list[str]] = []

            for comment_id, content in rows:
                cleaned = self.clean_text(str(content))
                if not cleaned:
                    continue
                tokens = self.tokenize(cleaned)
                if not tokens:
                    continue

                comment_ids.append(comment_id)
                cleaned_texts.append(cleaned)
                all_tokens.append(tokens)

            if not comment_ids:
                continue

            # 批量构建 Bigram
            bigram_tokens_list = self.build_bigrams(all_tokens)

            # 批量更新数据库
            for idx, comment_id in enumerate(comment_ids):
                await self.db.execute(
                    update(Comment)
                    .where(Comment.id == comment_id)
                    .values(
                        cleaned_content=cleaned_texts[idx],
                        tokens_json=json.dumps(all_tokens[idx], ensure_ascii=False),
                        bigram_tokens_json=json.dumps(
                            bigram_tokens_list[idx], ensure_ascii=False
                        ),
                        token_count=len(all_tokens[idx]),
                    )
                )

            await self.db.commit()
            total_processed += len(comment_ids)
            logger.info(f"已处理 {total_processed} 条评论...")

        logger.info(f"清洗完成，共处理 {total_processed} 条评论")
        return total_processed
