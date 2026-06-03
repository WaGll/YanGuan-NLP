"""
主题分析 API 路由

提供 LDA 主题建模结果的查询接口。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.common import APIResponse
from app.services.topic import TopicService

router = APIRouter(tags=["主题分析"])


@router.get("/topics")
async def get_topics(
    method: str = Query("lda", description="主题建模方法: lda / bertopic / hdbscan"),
    db: AsyncSession = Depends(get_db),
):
    """获取主题列表及每个主题的关键词。

    - **method**: 主题建模方法，目前仅支持 lda
    - 返回每个主题的标签、一致性分数、关键词列表及文档数量
    """
    service = TopicService(db)
    topics = await service.get_topics(method=method)
    return APIResponse(data=topics)
