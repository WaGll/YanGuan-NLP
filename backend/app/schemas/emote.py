"""
表情分析 API 响应模式
"""

from pydantic import BaseModel, Field


class EmoteItem(BaseModel):
    """单个表情项（用于频率排行）。"""

    name: str = Field(..., description="表情名称（不含括号）")
    frequency: int = Field(..., ge=0, description="全局出现总次数")
    comment_count: int = Field(..., ge=0, description="包含该表情的评论数（去重）")
    sentiment: str = Field(..., description="情感标签: positive / negative / neutral")
    percentage: float = Field(..., ge=0, le=100, description="占全部表情的百分比")


class EmoteSentimentBreakdown(BaseModel):
    """表情情感分布统计。"""

    positive: int = Field(0, ge=0)
    negative: int = Field(0, ge=0)
    neutral: int = Field(0, ge=0)
    total: int = Field(0, ge=0)
    positive_pct: float = 0.0
    negative_pct: float = 0.0
    neutral_pct: float = 0.0


class EmoteDetail(BaseModel):
    """单个表情详情。"""

    name: str
    frequency: int
    comment_count: int
    sentiment: str
    sample_comments: list[str] = Field(default_factory=list, description="包含该表情的评论样例")
    avg_text_sentiment: float | None = Field(None, description="包含该表情的评论平均情感分")


class EmoteSentimentCorrelation(BaseModel):
    """表情情感与文本情感的交叉分析。"""

    emote_name: str = Field(..., description="表情名称")
    emote_sentiment: str = Field(..., description="表情自身情感标签")
    avg_text_sentiment: float = Field(..., description="包含该表情的评论平均文本情感分")
    comment_count: int = Field(..., ge=0, description="包含该表情的评论数")
    sentiment_delta: float = Field(
        ..., description="文本情感分与表情预期情感的差值（正=文本比表情更正面）"
    )


class EmoteDistributionResponse(BaseModel):
    """表情分布接口完整响应。"""

    emotes: list[EmoteItem]
    sentiment_breakdown: EmoteSentimentBreakdown
    total_distinct_emotes: int
    total_emote_occurrences: int
