"""
语义网络模型

存储共现网络中的节点（关键词）和边（共现关系），
用于社区发现和网络可视化。
"""

from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class NetworkNode(Base, TimestampMixin):
    """语义网络节点表。

    每个节点代表一个关键词，存储其中心性指标和社区归属。
    """

    __tablename__ = "network_nodes"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="自增主键"
    )
    word: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True, comment="关键词"
    )
    frequency: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="词频"
    )
    degree_centrality: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="度中心性"
    )
    betweenness_centrality: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="介数中心性"
    )
    eigenvector_centrality: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="特征向量中心性"
    )
    community_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="社区ID（Louvain等算法结果）"
    )

    # --- 关联 ---
    outgoing_edges: Mapped[list["NetworkEdge"]] = relationship(
        "NetworkEdge",
        foreign_keys="NetworkEdge.source_word",
        back_populates="source",
        cascade="all, delete-orphan",
    )
    incoming_edges: Mapped[list["NetworkEdge"]] = relationship(
        "NetworkEdge",
        foreign_keys="NetworkEdge.target_word",
        back_populates="target",
        cascade="all, delete-orphan",
    )


class NetworkEdge(Base):
    """语义网络边表。

    每条边代表两个关键词之间的共现关系，权重为共现次数。
    """

    __tablename__ = "network_edges"
    __table_args__ = (
        UniqueConstraint("source_word", "target_word", name="uq_source_target"),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="自增主键"
    )
    source_word: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("network_nodes.word", ondelete="CASCADE"),
        nullable=False,
        comment="源节点（关键词）",
    )
    target_word: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("network_nodes.word", ondelete="CASCADE"),
        nullable=False,
        comment="目标节点（关键词）",
    )
    weight: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0, comment="共现权重"
    )

    # --- 关联 ---
    source: Mapped["NetworkNode"] = relationship(
        "NetworkNode", foreign_keys=[source_word], back_populates="outgoing_edges"
    )
    target: Mapped["NetworkNode"] = relationship(
        "NetworkNode", foreign_keys=[target_word], back_populates="incoming_edges"
    )
