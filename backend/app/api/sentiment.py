"""
情感分析 API 路由
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.sentiment import SentimentMLScore, SentimentResult
from app.schemas.common import APIResponse
from app.schemas.sentiment import SentimentBin, SentimentDistributionResponse

router = APIRouter(tags=["情感分析"])


@router.get("/sentiment", response_model=APIResponse[SentimentDistributionResponse])
async def get_sentiment(
    db: AsyncSession = Depends(get_db),
) -> APIResponse[SentimentDistributionResponse]:
    """获取情感分析分布。

    返回消极/中性/积极三个类别的评论数量、百分比，以及 ML 模型对比结果。
    """
    # 各类别数量
    result = await db.execute(
        select(
            SentimentResult.sentiment_class,
            func.count(SentimentResult.id),
        ).group_by(SentimentResult.sentiment_class)
    )
    rows = result.all()

    total = sum(r[1] for r in rows)
    bins = []
    label_map = {"negative": "消极", "neutral": "中性", "positive": "积极"}

    for label, count in rows:
        bins.append(
            SentimentBin(
                label=label_map.get(label, label),
                count=count,
                percentage=round(count / total * 100, 1) if total > 0 else 0.0,
            )
        )

    return APIResponse(
        data=SentimentDistributionResponse(bins=bins, total=total)
    )


@router.get("/sentiment/ml-scores")
async def get_ml_scores(
    db: AsyncSession = Depends(get_db),
):
    """获取 ML 模型交叉验证评估结果。"""
    result = await db.execute(
        select(
            SentimentMLScore.model_name,
            SentimentMLScore.cv_mean,
            SentimentMLScore.cv_std,
            SentimentMLScore.best_params_json,
        ).order_by(SentimentMLScore.cv_mean.desc())
    )
    rows = result.all()

    return APIResponse(data=[
        {
            "model_name": r[0],
            "cv_mean": round(float(r[1]), 4),
            "cv_std": round(float(r[2]), 4),
            "best_params": r[3],
        }
        for r in rows
    ])
