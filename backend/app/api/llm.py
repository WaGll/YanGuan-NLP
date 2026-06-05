"""
LLM 标签管理 API 路由

提供 LLM 标签精炼触发、缓存管理和健康检查。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config import settings
from app.schemas.common import APIResponse
from app.schemas.llm import (
    LLMCacheStatsResponse,
    LLMHealthResponse,
    LLMRelabelRequest,
    LLMRelabelResponse,
    TopicLabelRefinement,
)
from app.services.llm_labeler import LLMLabeler, get_cache

router = APIRouter(tags=["LLM 标签管理"])


@router.post("/llm/relabel")
async def trigger_relabel(
    body: LLMRelabelRequest,
    db: AsyncSession = Depends(get_db),
):
    """触发 LLM 重新标注已有主题。

    对数据库中已存在的主题（指定 method）重新运行 LLM 标签精炼。
    可用于主题建模完成后的标签优化，或规则标签不满意时的覆盖。

    - **method**: 主题建模方法 (lda / bertopic)
    """
    from app.services.topic import TopicService
    import time

    t_start = time.monotonic()
    service = TopicService(db)
    results = await service.relabel_topics(method=body.method)
    elapsed = round(time.monotonic() - t_start, 2)

    from_cache_count = sum(1 for r in results if r.get("from_cache"))

    return APIResponse(
        data=LLMRelabelResponse(
            method=body.method,
            topics_refined=[
                TopicLabelRefinement(
                    topic_index=r["topic_index"],
                    before=r.get("before", ""),
                    after=r["label"],
                    confidence=r["confidence"],
                    needs_review=r["needs_review"],
                    from_cache=r["from_cache"],
                )
                for r in results
            ],
            total=len(results),
            from_cache_count=from_cache_count,
            elapsed_seconds=elapsed,
        )
    )


@router.get("/llm/cache/stats")
async def get_llm_cache_stats():
    """获取 LLM 缓存统计。"""
    cache = get_cache()
    stats = cache.stats()
    return APIResponse(data=LLMCacheStatsResponse(**stats))


@router.delete("/llm/cache")
async def clear_llm_cache():
    """清空 LLM 标签缓存。"""
    cache = get_cache()
    count = cache.clear()
    return APIResponse(
        data={"cleared": count, "message": f"已清空 {count} 条缓存记录"}
    )


@router.get("/llm/health")
async def get_llm_health():
    """检查 Ollama 服务健康和模型状态。"""
    labeler = LLMLabeler()
    try:
        available = await labeler.health_check()
    finally:
        await labeler.close()

    return APIResponse(
        data=LLMHealthResponse(
            available=available,
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
        )
    )
