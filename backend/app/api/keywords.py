"""
关键词 API 路由
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.common import APIResponse
from app.services.keyword import KeywordService

router = APIRouter(tags=["关键词"])


@router.get("/keywords")
async def get_keywords(
    sort_by: str = Query("frequency", description="排序方式: frequency / tfidf"),
    limit: int = Query(50, ge=1, le=200, description="返回数量"),
    min_frequency: int = Query(3, ge=1, le=10000, description="最小词频过滤"),
    db: AsyncSession = Depends(get_db),
):
    """获取关键词列表及词云数据。"""
    service = KeywordService(db)
    keywords = await service.get_keywords(
        sort_by=sort_by,
        limit=limit,
        min_frequency=min_frequency,
    )
    wordcloud_data = await service.get_wordcloud_data(limit=limit)

    return APIResponse(data={
        "keywords": keywords,
        "wordcloud_data": wordcloud_data,
    })
