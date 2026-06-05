"""
Coherence 评估 API 请求/响应 Schema
"""

from pydantic import BaseModel, Field


class TopicScore(BaseModel):
    """单个主题的 coherence 信息。"""

    topic_index: int
    label: str
    business_label: str
    coherence_score: float = Field(..., description="c_v coherence 分数")
    quality_tier: str = Field(
        ..., description="质量分级: excellent / good / fair / poor"
    )


class MethodMetrics(BaseModel):
    """单个主题建模方法的 coherence 统计。"""

    method: str = Field(..., description="lda / bertopic")
    num_topics: int
    avg_coherence: float
    min_coherence: float
    max_coherence: float
    std_coherence: float
    topic_scores: list[TopicScore]


class CoherenceComparisonResponse(BaseModel):
    """LDA vs BERTopic 双轨对比响应。"""

    methods: list[MethodMetrics]
    winner: str | None = Field(None, description="胜出方法: lda / bertopic / tie")
    margin: float = Field(0.0, description="平均 coherence 差值 (winner - loser)")
    recommendation: str = Field("", description="人类可读的推荐说明")


class PerCommentCoherenceItem(BaseModel):
    """单条评论的 coherence 详情。"""

    comment_id: int
    content: str = Field("", description="评论原文（截断至 200 字）")
    primary_topic_id: int | None = None
    primary_topic_label: str | None = None
    primary_probability: float | None = None
    secondary_topic_id: int | None = None
    secondary_topic_label: str | None = None
    secondary_probability: float | None = None
    coherence_score: float | None = Field(None, description="评论与主主题的匹配度")
    is_mixed: bool = Field(False, description="是否为混合主题评论")


class MixedTopicItem(BaseModel):
    """混合主题评论详情。"""

    comment_id: int
    content: str = Field("", description="评论原文（截断至 200 字）")
    primary_topic: str
    primary_prob: float
    secondary_topic: str
    secondary_prob: float
    gap: float = Field(..., description="primary_prob - secondary_prob")


class CoherenceSummaryResponse(BaseModel):
    """Dashboard coherence 摘要。"""

    lda: MethodMetrics | None = None
    bertopic: MethodMetrics | None = None
    mixed_topic_count: int = 0
    mixed_topic_pct: float = 0.0
    total_comments_with_topics: int = 0
