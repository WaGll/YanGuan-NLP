"""
关键词 API 路由
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.keyword import Keyword
from app.schemas.common import APIResponse

router = APIRouter(tags=["关键词"])


@router.get("/keywords")
async def get_keywords(
    sort_by: str = Query("frequency", description="排序方式: frequency / tfidf"),
    limit: int = Query(50, ge=1, le=200, description="返回数量"),
    db: AsyncSession = Depends(get_db),
):
    """获取关键词列表及词云数据。"""
    order_col = Keyword.tfidf_score if sort_by == "tfidf" else Keyword.frequency

    result = await db.execute(
        select(Keyword.word, Keyword.frequency, Keyword.tfidf_score)
        .order_by(order_col.desc())
        .limit(limit)
    )
    rows = result.all()

    keywords = [
        {
            "word": r[0],
            "frequency": r[1],
            "tfidf_score": round(float(r[2]), 4) if r[2] else None,
        }
        for r in rows
    ]

    # 词云数据
    wordcloud_data = [{"name": r[0], "value": r[1]} for r in rows]

    return APIResponse(data={
        "keywords": keywords,
        "wordcloud_data": wordcloud_data,
    })
