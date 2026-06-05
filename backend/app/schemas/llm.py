"""
LLM 标签精炼 API 请求/响应 Schema
"""

from pydantic import BaseModel, Field


class TopicLabelRefinement(BaseModel):
    """单个主题的标签精炼结果。"""

    topic_index: int
    before: str = Field(..., description="精炼前标签（规则引擎）")
    after: str = Field(..., description="精炼后标签（LLM）")
    confidence: float = Field(..., description="置信度 0.0~1.0")
    needs_review: bool = Field(False, description="是否需要人工审核")
    from_cache: bool = Field(False, description="是否来自缓存")


class LLMRelabelRequest(BaseModel):
    """触发 LLM 重新标注的请求。"""

    method: str = Field("lda", description="主题建模方法: lda / bertopic")


class LLMRelabelResponse(BaseModel):
    """LLM 重新标注的响应。"""

    method: str
    topics_refined: list[TopicLabelRefinement]
    total: int
    from_cache_count: int
    elapsed_seconds: float


class LLMCacheStatsResponse(BaseModel):
    """LLM 缓存统计。"""

    size: int = Field(..., description="缓存条目数")
    hits: int = Field(..., description="命中次数")
    misses: int = Field(..., description="未命中次数")
    hit_rate: float = Field(..., description="命中率 0.0~1.0")


class LLMHealthResponse(BaseModel):
    """Ollama 健康检查与模型信息。"""

    available: bool
    model: str
    base_url: str
    labels_generated: int = Field(0, description="本会话中 LLM 生成的标签数")
