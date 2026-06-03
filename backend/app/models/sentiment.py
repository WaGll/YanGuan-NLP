"""
情感分析模型

存储 SnowNLP 情感评分、ML 模型预测结果及 ML 模型交叉验证指标。
"""

from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class SentimentResult(Base, TimestampMixin):
    """评论情感分析结果表。

    存储每条评论的 SnowNLP 评分、情感分类及可选的 ML 预测结果。
    """

    __tablename__ = "sentiment_results"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="自增主键"
    )
    comment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("comments.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        comment="评论ID（一对一）",
    )
    snownlp_score: Mapped[float] = mapped_column(
        Float, nullable=False, comment="SnowNLP 情感得分（0~1）"
    )
    sentiment_class: Mapped[Optional[str]] = mapped_column(
        String(16), nullable=True, comment="情感分类（positive/negative/neutral）"
    )
    ml_predicted: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="ML模型预测类别"
    )
    ml_confidence: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="ML模型预测置信度"
    )

    # --- 关联 ---
    comment: Mapped["Comment"] = relationship("Comment")


class SentimentMLScore(Base, TimestampMixin):
    """ML 情感模型评分表。

    存储不同 ML 模型的交叉验证指标及最佳超参数。
    """

    __tablename__ = "sentiment_ml_scores"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="自增主键"
    )
    model_name: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, comment="模型名称"
    )
    cv_mean: Mapped[float] = mapped_column(
        Float, nullable=False, comment="交叉验证平均得分"
    )
    cv_std: Mapped[float] = mapped_column(
        Float, nullable=False, comment="交叉验证标准差"
    )
    best_params_json: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="最佳超参数（JSON）"
    )
