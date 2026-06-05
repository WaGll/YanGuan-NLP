"""
情感分析服务

整合原 sentiment_analyzer.py 的核心逻辑：
  - SnowNLP 情感评分
  - ML 模型优化（SVM / RandomForest / LogisticRegression）
  - 修复了 TF-IDF 全局拟合导致数据泄漏的 Bug
"""

import json
import logging
from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC
from snownlp import SnowNLP
from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.models.sentiment import SentimentMLScore, SentimentResult

logger = logging.getLogger(__name__)

# 情感分类阈值（可被环境变量 GC_NEGATIVE_THRESHOLD / GC_POSITIVE_THRESHOLD 覆盖）
import os as _os
NEGATIVE_THRESHOLD = float(_os.environ.get("GC_NEGATIVE_THRESHOLD", 0.3))
POSITIVE_THRESHOLD = float(_os.environ.get("GC_POSITIVE_THRESHOLD", 0.7))


class SentimentService:
    """情感分析服务。

    提供 SnowNLP 基础情感评分和 ML 模型交叉验证优化。
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _snownlp_score(text: str) -> float:
        """计算单条文本的 SnowNLP 情感分。

        Args:
            text: 清洗后的评论文本

        Returns:
            情感分数 (0-1)，空文本返回 0.5
        """
        if not text or not isinstance(text, str) or not text.strip():
            return 0.5
        try:
            return float(SnowNLP(text).sentiments)
        except Exception:
            return 0.5

    @staticmethod
    def classify_sentiment(score: float) -> str:
        """将情感分数分类为 消极/中性/积极。"""
        if score <= NEGATIVE_THRESHOLD:
            return "negative"
        elif score >= POSITIVE_THRESHOLD:
            return "positive"
        return "neutral"

    async def compute_all(self, batch_size: int = 500, progress: bool = False) -> int:
        """批量计算所有评论的 SnowNLP 情感分数并持久化。

        Args:
            batch_size: 批次大小
            progress: 是否显示 tqdm 进度条

        Returns:
            处理的评论总数
        """
        total = 0

        # 总数预估（progress 模式）
        pbar = None
        if progress:
            from tqdm import tqdm
            from sqlalchemy import func, not_ as _not
            subq_count = select(SentimentResult.comment_id)
            total_result = await self.db.execute(
                select(func.count(Comment.id)).where(
                    Comment.cleaned_content.isnot(None),
                    Comment.id.not_in(subq_count),
                )
            )
            total_estimate = total_result.scalar() or 0
            if total_estimate > 0:
                pbar = tqdm(total=total_estimate, desc="Sentiment", unit="comments")

        while True:
            # 只查询尚未有情感结果的评论，避免无限循环
            from sqlalchemy import not_
            from sqlalchemy.orm import selectinload

            subq = select(SentimentResult.comment_id)
            result = await self.db.execute(
                select(Comment.id, Comment.cleaned_content)
                .where(
                    Comment.cleaned_content.isnot(None),
                    Comment.id.not_in(subq),
                )
                .limit(batch_size)
            )
            rows = result.all()
            if not rows:
                break

            for comment_id, cleaned in rows:
                score = self._snownlp_score(str(cleaned))
                sentiment_class = self.classify_sentiment(score)

                # 使用 INSERT OR REPLACE 模式
                existing = await self.db.execute(
                    select(SentimentResult.id).where(
                        SentimentResult.comment_id == comment_id
                    )
                )
                if existing.scalar():
                    await self.db.execute(
                        update(SentimentResult)
                        .where(SentimentResult.comment_id == comment_id)
                        .values(
                            snownlp_score=score,
                            sentiment_class=sentiment_class,
                        )
                    )
                else:
                    self.db.add(
                        SentimentResult(
                            comment_id=comment_id,
                            snownlp_score=score,
                            sentiment_class=sentiment_class,
                        )
                    )

            await self.db.commit()
            total += len(rows)
            if pbar:
                pbar.update(len(rows))
            else:
                logger.info(f"情感分析已处理 {total} 条...")

        if pbar:
            pbar.close()
        logger.info(f"情感分析完成，共处理 {total} 条评论")
        return total

    async def optimize_with_ml(self) -> dict[str, dict[str, Any]]:
        """
        使用 ML 模型优化情感分类。

        修复: 使用 sklearn Pipeline 将 TfidfVectorizer 与分类器封装，
        避免全局 fit_transform 导致的特征泄漏问题。

        Returns:
            {model_name: {cv_mean, cv_std, best_params}}
        """
        # 获取已标记的评论（使用 SnowNLP 分数 >0.6 作为正样本）
        result = await self.db.execute(
            select(Comment.cleaned_content, SentimentResult.snownlp_score)
            .join(SentimentResult, Comment.id == SentimentResult.comment_id)
            .where(Comment.cleaned_content.isnot(None))
        )
        rows = result.all()
        if not rows:
            logger.warning("无可用数据用于 ML 优化")
            return {}

        texts = [str(r[0]) for r in rows if r[0]]
        # 伪标签使用与 classify_sentiment() 相同的阈值，消除 train/serve skew
        labels = [int((r[1] or 0.5) >= POSITIVE_THRESHOLD) for r in rows if r[0]]

        if len(set(labels)) < 2:
            logger.warning("标签类别不足，跳过 ML 优化")
            return {}

        # 模型及参数网格（使用 Pipeline 避免特征泄漏）
        models = {
            "SVM": Pipeline([
                ("tfidf", TfidfVectorizer(max_features=5000)),
                ("clf", SVC(probability=True, random_state=42)),
            ]),
            "RandomForest": Pipeline([
                ("tfidf", TfidfVectorizer(max_features=5000)),
                ("clf", RandomForestClassifier(random_state=42)),
            ]),
            "LogisticRegression": Pipeline([
                ("tfidf", TfidfVectorizer(max_features=5000)),
                ("clf", LogisticRegression(max_iter=1000, random_state=42)),
            ]),
        }

        param_grids = {
            "SVM": {
                "clf__C": [0.1, 1, 10],
                "clf__kernel": ["linear", "rbf"],
            },
            "RandomForest": {
                "clf__n_estimators": [50, 100, 200],
            },
            "LogisticRegression": {
                "clf__C": [0.1, 1, 10],
            },
        }

        results: dict[str, dict[str, Any]] = {}

        for name, pipeline in models.items():
            grid = GridSearchCV(
                pipeline,
                param_grids[name],
                cv=5,
                scoring="accuracy",
                n_jobs=-1,
            )
            grid.fit(texts, labels)

            cv_mean = float(grid.best_score_)
            cv_std = float(grid.cv_results_["std_test_score"][grid.best_index_])

            # 持久化结果（使用 upsert 确保可重复运行）
            stmt = (
                sqlite_insert(SentimentMLScore)
                .values(
                    model_name=name,
                    cv_mean=cv_mean,
                    cv_std=cv_std,
                    best_params_json=json.dumps(grid.best_params_, ensure_ascii=False),
                )
                .on_conflict_do_update(
                    index_elements=["model_name"],
                    set_={
                        "cv_mean": cv_mean,
                        "cv_std": cv_std,
                        "best_params_json": json.dumps(grid.best_params_, ensure_ascii=False),
                    },
                )
            )
            await self.db.execute(stmt)

            results[name] = {
                "cv_mean": round(cv_mean, 4),
                "cv_std": round(cv_std, 4),
                "best_params": grid.best_params_,
            }

            logger.info(f"{name}: CV accuracy = {cv_mean:.4f} +/- {cv_std:.4f}")

        await self.db.flush()
        return results

    @staticmethod
    def calibrate_thresholds(scores: list[float]) -> dict[str, float]:
        """数据驱动的阈值校准。

        基于分数分布的 25th/75th 百分位推算建议阈值。
        仅输出建议，不自动覆盖（需手动设环境变量）。

        Returns:
            {negative_threshold, positive_threshold, mean, median, std, n}
        """
        if len(scores) < 100:
            return {"negative_threshold": NEGATIVE_THRESHOLD,
                    "positive_threshold": POSITIVE_THRESHOLD,
                    "mean": 0.0, "median": 0.0, "std": 0.0, "n": len(scores)}
        arr = np.array([s for s in scores if 0 < s < 1])  # 排除极端值
        return {
            "negative_threshold": round(float(np.percentile(arr, 25)), 3),
            "positive_threshold": round(float(np.percentile(arr, 75)), 3),
            "mean": round(float(arr.mean()), 3),
            "median": round(float(np.median(arr)), 3),
            "std": round(float(arr.std()), 3),
            "n": len(arr),
        }

    async def get_distribution(self) -> list[dict[str, Any]]:
        """获取情感分布统计。

        Returns:
            [{label: str, count: int, percentage: float}, ...]
        """
        result = await self.db.execute(
            select(
                SentimentResult.sentiment_class,
                __import__("sqlalchemy").func.count(SentimentResult.id),
            ).group_by(SentimentResult.sentiment_class)
        )
        rows = result.all()

        total = sum(r[1] for r in rows)
        distribution = []
        for label, count in rows:
            distribution.append({
                "label": label,
                "count": count,
                "percentage": round(count / total * 100, 1) if total > 0 else 0.0,
            })

        return distribution
