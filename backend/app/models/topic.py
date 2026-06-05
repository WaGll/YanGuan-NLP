"""
主题模型

存储 LDA / BERTopic / HDBSCAN 等主题建模结果，
包含主题本身、主题-关键词关联、文档-主题分配。
"""

from typing import Optional

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Topic(Base, TimestampMixin):
    """主题表。

    存储一种主题建模方法产生的所有主题。
    """

    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="自增主键"
    )
    method: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="主题建模方法（lda/bertopic/hdbscan）"
    )
    topic_index: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="主题编号（从0开始）"
    )
    label: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="主题标签/名称（关键词拼接）"
    )
    business_label: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, comment="业务主题标签（自动生成）"
    )
    coherence_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="一致性分数"
    )
    silhouette_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="轮廓系数 / NPMI score（BERTopic复用）"
    )
    business_label_llm: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, comment="LLM 精炼后的业务主题标签"
    )
    business_label_confidence: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="业务标签置信度（0~1）"
    )
    needs_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否需要人工审核标签"
    )

    # --- 关联 ---
    keywords: Mapped[list["TopicKeyword"]] = relationship(
        "TopicKeyword", back_populates="topic", cascade="all, delete-orphan"
    )
    doc_assignments: Mapped[list["DocTopic"]] = relationship(
        "DocTopic", back_populates="topic", cascade="all, delete-orphan"
    )


class TopicKeyword(Base):
    """主题关键词表。

    记录每个主题下排名靠前的关键词及其权重。
    """

    __tablename__ = "topic_keywords"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="自增主键"
    )
    topic_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, comment="主题ID"
    )
    word: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="关键词"
    )
    weight: Mapped[float] = mapped_column(
        Float, nullable=False, comment="关键词权重"
    )
    rank: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="排名（1为最高）"
    )

    # --- 关联 ---
    topic: Mapped["Topic"] = relationship("Topic", back_populates="keywords")


class DocTopic(Base):
    """文档-主题分配表。

    记录每条评论被分配到某个主题的概率。
    """

    __tablename__ = "doc_topics"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="自增主键"
    )
    comment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("comments.id", ondelete="CASCADE"), nullable=False, comment="评论ID"
    )
    topic_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, comment="主题ID"
    )
    probability: Mapped[float] = mapped_column(
        Float, nullable=False, comment="属于该主题的概率"
    )
    is_primary: Mapped[bool] = mapped_column(
        Integer, nullable=False, default=0, comment="是否为主要主题"
    )

    # --- 关联 ---
    topic: Mapped["Topic"] = relationship("Topic", back_populates="doc_assignments")
    comment: Mapped["Comment"] = relationship("Comment")

    # --- 导入后向引用 ---
    # 避免循环导入，在模块末尾建立关系
