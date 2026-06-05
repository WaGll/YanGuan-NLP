"""主题建模 schema。"""

from pydantic import BaseModel, Field


class TopicKeywordItem(BaseModel):
    """主题关键词条目。"""

    word: str = Field(..., description="关键词")
    weight: float = Field(..., ge=0.0, description="关键词权重")
    rank: int = Field(..., ge=0, description="排名序号")


class TopicItem(BaseModel):
    """单个主题条目。"""

    id: int = Field(..., description="主题数据库 ID")
    topic_index: int = Field(..., ge=0, description="主题序号（从 0 开始）")
    label: str | None = Field(None, description="主题标签（关键词拼接）")
    business_label: str | None = Field(None, description="业务主题标签（自动生成）")
    method: str = Field(..., description="建模方法: lda / bertopic")
    coherence_score: float | None = Field(None, description="一致性得分")
    doc_count: int = Field(default=0, ge=0, description="分配给此主题的文档数")
    keywords: list[TopicKeywordItem] = Field(default_factory=list, description="Top 关键词列表")


class TopicDetailResponse(BaseModel):
    """单个主题详情（含代表性评论）。"""

    topic: TopicItem
    representative_comments: list[str] = Field(
        default_factory=list, description="代表性评论文本（最多 10 条）"
    )
    keyword_count: int = Field(default=0, ge=0, description="该主题的总关键词数")


class TopicsResponse(BaseModel):
    """主题列表响应。"""

    topics: list[TopicItem] = Field(default_factory=list)
    method: str = Field(default="lda", description="使用的建模方法")
    total: int = Field(default=0, ge=0, description="主题总数")
