"""
基础模型模块

提供声明式基类和时间戳混入类。
"""

import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """所有模型的声明式基类。"""
    pass


class TimestampMixin:
    """时间戳混入类，为模型添加 created_at / updated_at 字段。

    用法:
        class MyModel(Base, TimestampMixin):
            __tablename__ = "my_table"
            id: Mapped[int] = mapped_column(primary_key=True)
    """

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        comment="记录创建时间",
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="记录最后更新时间",
    )
