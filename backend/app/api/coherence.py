"""
Coherence 评估 API 路由

提供 LDA vs BERTopic 双轨对比、逐评论 coherence、混合主题检测。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.coherence import (
    CoherenceComparisonResponse,
    CoherenceSummaryResponse,
    PerCommentCoherenceItem,
    MixedTopicItem,
)
from app.schemas.common import APIResponse
from app.services.coherence import CoherenceService

router = APIRouter(tags=["Coherence 评估"])


@router.get("/coherence/compare")
async def compare_coherence(
    db: AsyncSession = Depends(get_db),
):
    """LDA vs BERTopic 双轨 coherence 对比。

    返回两种方法的逐主题 coherence 指标及胜者推荐。
    """
    service = CoherenceService(db)
    result = await service.compare_methods()
    return APIResponse(data=CoherenceComparisonResponse(**result))


@router.get("/coherence/per-comment")
async def get_per_comment_coherence(
    method: str = Query("lda", description="主题建模方法: lda / bertopic"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """批量获取逐评论 coherence（分页）。

    - 每项包含评论与主次主题的匹配概率和 coherence 分数
    - 按主主题概率降序排列
    """
    service = CoherenceService(db)
    result = await service.get_all_per_comment_coherence(
        method=method, page=page, page_size=page_size,
    )
    items = [PerCommentCoherenceItem(**item) for item in result["items"]]
    return APIResponse(data={
        "items": [item.model_dump() for item in items],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
    })


@router.get("/coherence/per-comment/{comment_id}")
async def get_single_comment_coherence(
    comment_id: int,
    method: str = Query("lda", description="主题建模方法: lda / bertopic"),
    db: AsyncSession = Depends(get_db),
):
    """获取单条评论的 coherence 详情。

    包含主次主题分配、匹配概率和 coherence 分数。
    """
    service = CoherenceService(db)
    result = await service.get_per_comment_coherence(comment_id, method=method)
    if result is None:
        return APIResponse(data=None, code=404, message="该评论无主题分配")
    return APIResponse(data=PerCommentCoherenceItem(**result))


@router.get("/coherence/mixed-topics")
async def get_mixed_topics(
    threshold: float = Query(0.30, ge=0.10, le=0.50, description="次主题概率阈值"),
    method: str = Query("lda", description="主题建模方法: lda / bertopic"),
    limit: int = Query(100, ge=1, le=500, description="最大返回数"),
    db: AsyncSession = Depends(get_db),
):
    """检测混合主题评论。

    返回次主题概率高于阈值且主主题概率低于 0.50 的评论。
    按 gap 升序排列（最靠近双主题的在前）。
    """
    service = CoherenceService(db)
    items = await service.detect_mixed_topics(
        threshold=threshold, method=method, limit=limit,
    )
    return APIResponse(data=[MixedTopicItem(**item) for item in items])


@router.get("/coherence/summary")
async def get_coherence_summary(
    db: AsyncSession = Depends(get_db),
):
    """Dashboard coherence 摘要。

    包含 LDA/BERTopic 指标、混合主题占比。
    """
    service = CoherenceService(db)
    result = await service.get_summary()
    return APIResponse(data=CoherenceSummaryResponse(**result))
