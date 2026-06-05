"""
表情分析模型 — EmoteType (表情类型) + CommentEmote (评论-表情关联)
"""

import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class EmoteType(Base, TimestampMixin):
    """B站方括号表情类型（如 doge、大哭、星星眼 等）。

    全局聚合表：存储每种表情的频次、情感标签和统计信息。
    """

    __tablename__ = "emote_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True,
        comment="表情名称（不含括号），如 doge、大哭",
    )
    frequency: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="全局出现总次数",
    )
    sentiment: Mapped[str] = mapped_column(
        String(16), nullable=False, default="neutral",
        comment="情感标签：positive / negative / neutral",
    )
    comment_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="包含该表情的评论数（去重）",
    )
    first_seen: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, nullable=True,
    )
    last_seen: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, nullable=True,
    )

    # 关系
    comment_emotes: Mapped[list["CommentEmote"]] = relationship(
        "CommentEmote", back_populates="emote",
    )

    def __repr__(self) -> str:
        return f"<EmoteType '{self.name}' freq={self.frequency}>"


class CommentEmote(Base):
    """评论与表情的关联表（多对多）。

    记录每条评论使用了哪些表情及出现位置。
    """

    __tablename__ = "comment_emotes"
    __table_args__ = (
        UniqueConstraint(
            "comment_id", "emote_id", "position",
            name="uq_comment_emote_position",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    comment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=False, index=True,
        comment="关联评论ID",
    )
    emote_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("emote_types.id", ondelete="CASCADE"),
        nullable=False, index=True,
        comment="关联表情类型ID",
    )
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="表情在原文中的起始字符位置",
    )

    # 关系
    comment: Mapped["Comment"] = relationship("Comment")  # noqa: F821
    emote: Mapped["EmoteType"] = relationship("EmoteType", back_populates="comment_emotes")

    def __repr__(self) -> str:
        return f"<CommentEmote comment={self.comment_id} emote={self.emote_id}>"
