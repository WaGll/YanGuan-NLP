# Template: 新建 SQLAlchemy 模型

## 使用说明

复制此模板创建新的 ORM 模型。替换 `{{placeholders}}`。

## 文件位置
`backend/app/models/{{module_name}}.py`

## 模板

```python
"""
{{模型中文名}}数据模型

{{功能描述}}
"""

import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Float, Integer, String, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class {{ModelName}}(Base, TimestampMixin):
    """{{模型中文名}}模型。

    {{详细描述}}
    """

    __tablename__ = "{{table_name}}"

    # --- 主键 ---
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="自增主键"
    )

    # --- 业务字段 ---
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="{{字段说明}}"
    )
    value: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="{{字段说明}}"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="{{字段说明}}"
    )

    # --- 外键（如有） ---
    # parent_id: Mapped[int] = mapped_column(
    #     Integer,
    #     ForeignKey("parent_table.id", ondelete="CASCADE"),
    #     nullable=False,
    #     comment="父记录ID",
    # )

    # --- 关联关系（如有） ---
    # parent: Mapped["ParentModel"] = relationship(
    #     "ParentModel",
    #     back_populates="children",
    #     lazy="selectin",
    # )

    def __repr__(self) -> str:
        return f"<{{ModelName}}(id={self.id}, name={self.name})>"
```

## 注册模型

创建文件后，必须在 `backend/app/models/__init__.py` 中加入导入：

```python
from app.models.{{module_name}} import {{ModelName}}  # noqa: F401
```

这确保 `Base.metadata.create_all()` 能发现新表。

## 字段类型速查

| Python 类型 | SQLAlchemy 类型 | 使用场景 |
|------------|----------------|---------|
| `int` | `Integer` | 主键、计数器 |
| `int` | `BigInteger` | Unix 时间戳 |
| `str` | `String(N)` | 有限长度字符串（N=最大字符数） |
| `str` | `Text` | 无限制文本（评论内容、JSON） |
| `float` | `Float` | 小数 |
| `datetime` | `DateTime` | 日期时间 |
| `bool` | `Boolean` | 是否为真 |

## 约束速查

| 约束 | 语法 | 示例 |
|------|------|------|
| 唯一 | `unique=True` | `comment_id` |
| 非空 | `nullable=False` | 核心字段 |
| 索引 | `index=True` | 外键和高频查询字段 |
| 外键 | `ForeignKey("table.column")` | 关联字段 |
| 默认值 | `server_default=func.now()` | 时间戳 |

## 清单

添加新模型时需要检查：
- [ ] 文件放在 `backend/app/models/` 下
- [ ] 继承 `Base` 和 `TimestampMixin`
- [ ] `__tablename__` 用复数形式
- [ ] 所有列有 `comment` 参数（中文说明）
- [ ] 主键使用 `autoincrement=True`
- [ ] 外键字段有 `index=True`
- [ ] 在 `__init__.py` 中导入
- [ ] 更新 `memory/database-schema.md` 中的表列表
