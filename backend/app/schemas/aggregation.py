"""
聚合 API 请求/响应 Schema
"""

from pydantic import BaseModel, Field


class AggregationConfigRequest(BaseModel):
    """运行时更新聚合配置的请求。"""

    window_minutes: int | None = Field(
        None, ge=10, le=1440, description="时间窗口大小（分钟）"
    )
    min_comments: int | None = Field(
        None, ge=1, le=100, description="每组最少评论数"
    )
    enabled: bool | None = Field(None, description="启用/禁用聚合")


class AggregationConfigResponse(BaseModel):
    """当前聚合配置。"""

    enabled: bool
    window_minutes: int
    min_comments: int


class AggregationStatusResponse(BaseModel):
    """聚合状态统计。"""

    total_groups: int = Field(..., description="CommentGroup 总记录数")
    total_comments_aggregated: int = Field(..., description="聚合覆盖的评论数")
    total_comments_total: int = Field(..., description="数据库中已清洗评论总数")
    coverage_pct: float = Field(..., description="聚合覆盖率（百分比）")
    distinct_videos: int = Field(..., description="不同视频数")
    avg_group_size: float = Field(..., description="平均每组评论数")
    max_group_size: int = Field(..., description="最大组评论数")
    size_distribution: list[dict] = Field(
        default_factory=list,
        description="组大小分布 [{\"comment_count\": N, \"group_count\": M}, ...]",
    )


class AggregationRunResponse(BaseModel):
    """触发生新聚合的响应。"""

    groups_created: int = Field(..., description="创建的聚合组数")
    comments_processed: int = Field(..., description="处理的评论数")
    window_minutes: int
    min_comments: int
    elapsed_seconds: float = Field(..., description="耗时（秒）")
