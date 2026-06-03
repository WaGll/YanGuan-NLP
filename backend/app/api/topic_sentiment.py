"""
主题-情感联合分析 API 路由

提供主题与情感分类交叉分析的热力图矩阵数据。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.common import APIResponse
from app.services.topic_sentiment import TopicSentimentService

router = APIRouter(tags=["主题-情感联合分析"])


@router.get("/topic-sentiment")
async def get_topic_sentiment(
    method: str = Query("lda", description="主题建模方法: lda / bertopic / hdbscan"),
    db: AsyncSession = Depends(get_db),
):
    """获取主题-情感联合分布矩阵（热力图数据）。

    - **method**: 主题建模方法，目前仅支持 lda
    - 返回 topics（横轴标签）、sentiment_classes（纵轴标签）及 cells（二维矩阵）
    - 每个单元格包含 count（数量）和 proportion（占比）
    """
    service = TopicSentimentService(db)
    matrix = await service.compute_joint_matrix(method=method)
    return APIResponse(data=matrix)
