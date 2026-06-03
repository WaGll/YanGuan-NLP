"""Sentiment analysis schemas: distribution bins and aggregated responses."""

from pydantic import BaseModel, Field


class SentimentBin(BaseModel):
    """单个情感分桶 / A single sentiment distribution bin.

    Used to represent how many comments fall into a sentiment range:
    - negative:  [0.0,  0.4)
    - neutral:   [0.4,  0.6)
    - positive:  [0.6,  1.0]
    """

    label: str = Field(
        ...,
        description="分桶标签：positive / neutral / negative",
        examples=["positive", "neutral", "negative"],
    )
    count: int = Field(
        ...,
        description="该桶内的评论数量 / Number of comments in this bin",
        ge=0,
    )
    percentage: float = Field(
        ...,
        description="该桶百分比 (0-100) / Percentage share of this bin",
        ge=0.0,
        le=100.0,
    )


class SentimentDistributionResponse(BaseModel):
    """情感分布接口响应 / Sentiment distribution API response.

    Contains the full breakdown of sentiment across all analyzed comments.
    """

    bins: list[SentimentBin] = Field(
        ...,
        description="情感分桶列表 / Ordered list of sentiment bins",
    )
    total: int = Field(
        ...,
        description="参与统计的总评论数 / Total comments included in this distribution",
        ge=0,
    )
