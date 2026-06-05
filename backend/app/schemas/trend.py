"""趋势分析 schema。"""

from datetime import datetime

from pydantic import BaseModel, Field


class TrendBucket(BaseModel):
    """单个时间桶的趋势数据点。"""

    bucket_start: str = Field(..., description="时间桶起始时间 (ISO 8601)")
    bucket_end: str = Field(..., description="时间桶结束时间 (ISO 8601)")
    avg_sentiment: float | None = Field(None, description="平均情感得分 (0~1)")
    comment_count: int = Field(..., ge=0, description="该时段评论数")
    positive_count: int = Field(default=0, ge=0, description="积极评论数")
    neutral_count: int = Field(default=0, ge=0, description="中性评论数")
    negative_count: int = Field(default=0, ge=0, description="消极评论数")


class TrendResponse(BaseModel):
    """趋势分析响应。"""

    series_type: str = Field(..., description="趋势类型: sentiment / volume")
    granularity: str = Field(..., description="时间粒度: day / week / month / year")
    buckets: list[TrendBucket] = Field(default_factory=list, description="时间序列数据桶")
    total_points: int = Field(default=0, ge=0, description="数据点总数")
