"""Dashboard overview: high-level metrics for the platform landing page."""

from datetime import datetime

from pydantic import BaseModel, Field


class DashboardOverview(BaseModel):
    """看板概览数据 / Dashboard overview metrics.

    Aggregated from the comments table after the full NLP pipeline has run.
    """

    total_comments: int = Field(
        ...,
        description="已导入的总评论数 / Total number of imported comments",
        ge=0,
    )
    unique_users: int = Field(
        ...,
        description="去重用户数 / Number of unique users",
        ge=0,
    )
    date_range_start: datetime | None = Field(
        default=None,
        description="最早评论时间 / Earliest comment timestamp in the dataset",
    )
    date_range_end: datetime | None = Field(
        default=None,
        description="最晚评论时间 / Latest comment timestamp in the dataset",
    )
    avg_sentiment: float = Field(
        ...,
        description="平均情感得分 (0-1) / Average sentiment score across all comments [0-1]",
        ge=0.0,
        le=1.0,
    )
