"""
文本清洗与分词服务

整合原 data_cleaner.py 的核心逻辑，修复了中文 \\b 正则 bug。
作为无状态服务，支持批量处理和单条处理。
"""

import json
import logging
import unicodedata
from pathlib import Path
from typing import Optional

# 过滤 jieba 的 pkg_resources 弃用警告
import warnings
warnings.filterwarnings("ignore", message="pkg_resources is deprecated", category=UserWarning)

import jieba
from gensim.models.phrases import Phrases
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.utils.chinese import clean_chinese_text
from app.utils.resources import NLPResources
from app.utils.tokenizer import ChineseTokenizer, TokenizerBackend
from app.config import settings

logger = logging.getLogger(__name__)


class CleanerService:
    """文本清洗与分词服务。

    依赖 NLPResources 单例获取停用词和同义词，
    对评论执行清洗 → 分词 → 同义词替换 → Bigram 短语挖掘。
    支持 pkuseg 和 jieba 两种分词后端，通过 GC_TOKENIZER_BACKEND 配置切换。
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.resources = NLPResources.get_instance()

        if not self.resources.is_loaded:
            raise RuntimeError(
                "NLPResources 尚未加载，请先调用 NLPResources.get_instance().load(data_dir)"
            )

        # 根据配置创建分词器
        backend = TokenizerBackend(settings.tokenizer_backend)
        data_dir = settings.data_dir

        # pkuseg 使用专用的用户词典（每行一个词），jieba 使用原有格式
        if backend == TokenizerBackend.PKUSEG:
            pkuseg_dict = data_dir / "pkuseg_dict.txt"
            user_dict = pkuseg_dict if pkuseg_dict.exists() else None
        else:
            user_dict = settings.resolve_custom_dict_path()

        self._tokenizer = ChineseTokenizer(
            backend=backend,
            data_dir=data_dir,
            user_dict_path=user_dict,
            pos_filter=True,
        )
        logger.info("CleanerService 使用分词后端: %s", self._tokenizer.backend.value)

    def clean_text(self, text: str) -> str:
        """清洗单条评论文本。

        Args:
            text: 原始评论文本

        Returns:
            清洗后的文本
        """
        return clean_chinese_text(text)

    @staticmethod
    def _is_valid_token(token: str) -> bool:
        """Token 级噪声过滤：拒绝空白、标点、纯数字、单字。

        在停用词过滤之后、同义词替换之前调用。
        单中文字（如"说""人""考"）对主题建模和关键词分析没有独立的业务价值。
        纯数字（如 660、408）是课程编号/分数线，不应出现在主题关键词中。
        考研学科代码（432, 396, 301）已通过自定义词典以复合词形式保留。
        """
        if not token or not token.strip():
            return False
        if token.isdigit():
            return False
        if len(token) == 1:
            return False
        cat = unicodedata.category(token[0])
        if cat.startswith("P") or cat.startswith("S") or cat.startswith("Z"):
            return False
        return True

    def tokenize(self, text: str) -> list[str]:
        """对清洗后的文本进行分词。

        步骤: 分词(pkuseg/jieba) → 过滤停用词 → token级噪声过滤 → 同义词替换

        当 tokenizer_backend="pkuseg" 时，词性噪声在分词阶段已过滤，
        额外进行停用词和 token 级噪声过滤作为第二道防线。

        Args:
            text: 清洗后的文本

        Returns:
            分词结果列表
        """
        if not text:
            return []

        # 使用统一分词器（pkuseg 已内置词性过滤）
        tokens = self._tokenizer.tokenize(text)

        # 过滤停用词
        tokens = [
            w for w in tokens
            if w not in self.resources.stopwords
        ]
        # Token 级噪声过滤：空白、标点、纯数字、单字
        tokens = [w for w in tokens if self._is_valid_token(w)]
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

    async def process_all(self, batch_size: int = 500, progress: bool = False) -> int:
        """批量处理数据库中所有未处理的评论。

        读取所有评论 → 清洗 → 分词 → Bigram → 更新数据库。

        Args:
            batch_size: 每批处理数量
            progress: 是否显示 tqdm 进度条

        Returns:
            处理的评论总数
        """
        total_processed = 0

        # 总数预估（progress 模式）
        pbar = None
        if progress:
            from tqdm import tqdm
            from sqlalchemy import func
            total_result = await self.db.execute(
                select(func.count(Comment.id)).where(
                    Comment.content.isnot(None),
                    Comment.cleaned_content.is_(None),
                )
            )
            total_estimate = total_result.scalar() or 0
            if total_estimate > 0:
                pbar = tqdm(total=total_estimate, desc="Cleaning", unit="comments")

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
                tokens = self.tokenize(cleaned) if cleaned else []

                # 无论如何都标记为已处理，避免空内容评论被反复查询（无限循环）
                comment_ids.append(comment_id)
                cleaned_texts.append(cleaned)
                all_tokens.append(tokens)

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
            if pbar:
                pbar.update(len(comment_ids))
            else:
                logger.info(f"已处理 {total_processed} 条评论...")

        if pbar:
            pbar.close()
        logger.info(f"清洗完成，共处理 {total_processed} 条评论")
        return total_processed
