"""
评论聚合模型

存储按视频 + 时间窗口聚合后的伪文档，用于缓解短文本语义稀疏。
"""

import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class CommentGroup(Base, TimestampMixin):
    """视频+时间窗口聚合后的伪文档。

    将同一视频下、同一时间窗口内的多条短评论合并为一条
    聚合文档，提升单条文档的语义丰富度，改善主题建模质量。
    """

    __tablename__ = "comment_groups"

    # --- 主键 ---
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="自增主键"
    )

    # --- 聚合维度 ---
    video_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, comment="来源视频ID"
    )
    time_window_start: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, comment="时间窗口起始"
    )
    time_window_end: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, comment="时间窗口结束"
    )

    # --- 聚合内容 ---
    comment_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="组内评论数"
    )
    aggregated_content: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="合并后的原始文本（空格分隔）"
    )
    aggregated_tokens_json: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="合并后的分词结果（JSON列表）"
    )
    unique_comment_ids: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="来源评论ID列表（JSON数组）"
    )

    # --- 标记 ---
    is_aggregated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否为聚合文档"
    )
