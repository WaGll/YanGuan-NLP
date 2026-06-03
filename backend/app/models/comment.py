"""
评论模型

对应原始 CSV 中 blbl_comments 表结构，保留所有原始字段，
同时扩展清洗后的分析字段。
"""

import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Comment(Base, TimestampMixin):
    """B站评论数据模型。

    保留原始 CSV 全部字段，同时提供清洗后用于分析的分词/去重字段。
    """

    __tablename__ = "comments"

    # --- 主键 ---
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="自增主键"
    )

    # --- 原始字段（与 CSV 列一一对应，修复了旧代码丢列的问题） ---
    comment_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True, comment="评论唯一ID"
    )
    parent_comment_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="父评论ID（子评论才有）"
    )
    create_time: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="评论创建Unix时间戳"
    )
    create_datetime: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, nullable=True, comment="评论创建时间（datetime格式）"
    )
    video_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True, comment="视频ID"
    )
    content: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="评论原始内容"
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="用户ID"
    )
    nickname: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="用户昵称"
    )
    avatar: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="用户头像URL"
    )
    sub_comment_count: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="子评论数"
    )
    last_modify_ts: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="最后修改时间戳"
    )

    # --- 清洗后的分析字段 ---
    cleaned_content: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="清洗后的评论内容"
    )
    tokens_json: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="分词结果（JSON列表）"
    )
    bigram_tokens_json: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="二元词组分词结果（JSON列表）"
    )
    token_count: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="有效分词数量"
    )
