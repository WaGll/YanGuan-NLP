"""
关键词模型

存储 TF-IDF / TextRank 等算法提取的关键词及其统计信息。
"""

from typing import Optional

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Keyword(Base, TimestampMixin):
    """关键词表。

    存储从评论中提取的关键词及其频率、权重等统计信息。
    """

    __tablename__ = "keywords"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="自增主键"
    )
    word: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True, comment="关键词"
    )
    frequency: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="词频"
    )
    tfidf_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="TF-IDF 权重"
    )
    pos_tag: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, comment="词性标注"
    )
