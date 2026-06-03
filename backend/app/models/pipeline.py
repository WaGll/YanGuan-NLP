"""
流水线执行记录模型

追踪数据处理流水线中各阶段的执行状态、耗时和错误信息。
"""

import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PipelineRun(Base):
    """流水线运行记录表。

    每次触发分析流水线时创建一条记录，追踪各阶段状态。
    """

    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="自增主键"
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="pending",
        comment="运行状态（pending/running/completed/failed）",
    )
    stage: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="当前阶段名称"
    )
    started_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, nullable=True, comment="开始时间"
    )
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, nullable=True, comment="完成时间"
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="错误信息"
    )
    metadata_json: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="附加元数据（JSON）"
    )
