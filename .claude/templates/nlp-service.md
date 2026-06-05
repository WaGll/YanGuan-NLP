# Template: 新建 Service 层

## 使用说明

复制此模板创建新的 Service 类。替换 `{{placeholders}}`。

## 文件位置
`backend/app/services/{{module_name}}.py`

## 模板

```python
"""
{{服务中文名}}服务

{{功能描述}}
"""

import json
import logging
from typing import Any

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.{{model_file}} import {{ModelName}}

logger = logging.getLogger(__name__)


class {{ServiceName}}Service:
    """{{服务中文名}}服务。

    {{详细描述}}
    """

    def __init__(self, db: AsyncSession):
        """初始化服务。

        Args:
            db: 异步数据库会话（由 FastAPI Depends 注入）
        """
        self.db = db

    # ------------------------------------------------------------------
    # 公开方法
    # ------------------------------------------------------------------

    async def process_all(self, batch_size: int = 500) -> dict[str, Any]:
        """批量处理所有未处理的数据。

        Args:
            batch_size: 每批处理的数据量

        Returns:
            处理结果摘要，包含:
            - processed_count: 处理的记录数
            - error_count: 失败的记录数
        """
        processed = 0
        errors = 0

        try:
            while True:
                batch = await self._fetch_batch(batch_size)
                if not batch:
                    break

                for item in batch:
                    try:
                        await self._process_one(item)
                        processed += 1
                    except Exception as e:
                        logger.error(f"处理 {{ModelName}} id={item.id} 失败: {e}")
                        errors += 1

                await self.db.commit()
                logger.info(f"{{ServiceName}}Service: 已处理 {processed} 条...")

        except Exception as e:
            await self.db.rollback()
            logger.error(f"{{ServiceName}}Service 致命错误: {e}")
            raise

        logger.info(f"{{ServiceName}}Service 完成: {processed} 成功, {errors} 失败")
        return {"processed_count": processed, "error_count": errors}

    async def get_results(self, **filters: Any) -> list[dict[str, Any]]:
        """获取分析结果。

        Args:
            **filters: 可选的过滤参数

        Returns:
            结果字典列表
        """
        query = select({{ModelName}})

        # 应用过滤条件
        if "key" in filters:
            query = query.where({{ModelName}}.key == filters["key"])

        result = await self.db.execute(query)
        items = result.scalars().all()

        return [self._serialize(item) for item in items]

    # ------------------------------------------------------------------
    # 私有方法
    # ------------------------------------------------------------------

    async def _fetch_batch(self, batch_size: int) -> list[{{ModelName}}]:
        """获取一批待处理的数据。

        Args:
            batch_size: 批次大小

        Returns:
            {{ModelName}} 实例列表
        """
        result = await self.db.execute(
            select({{ModelName}})
            .where({{ModelName}}.processed.is_(False))
            .limit(batch_size)
        )
        return list(result.scalars().all())

    async def _process_one(self, item: {{ModelName}}) -> None:
        """处理单条数据。

        Args:
            item: 待处理的 {{ModelName}} 实例
        """
        # 在这里实现核心处理逻辑
        # 处理完成后更新 item 的状态
        item.processed = True
        # item.result = computed_result

    @staticmethod
    def _serialize(item: {{ModelName}}) -> dict[str, Any]:
        """将 ORM 模型序列化为字典。

        Args:
            item: {{ModelName}} 实例

        Returns:
            序列化后的字典
        """
        return {
            "id": item.id,
            # 添加其他字段...
        }
```

## 清单

添加新 Service 时需要检查：
- [ ] 文件放在 `backend/app/services/` 下
- [ ] 类名使用 `{{Name}}Service` 形式
- [ ] 构造函数接受 `db: AsyncSession`
- [ ] 公开方法使用 `async/await`
- [ ] 批量处理分批（batch_size=500）
- [ ] 错误不会静默吞掉（至少 logger.error）
- [ ] 私有方法前缀 `_`
- [ ] 序列化方法从 ORM → dict
- [ ] 在 `backend/app/services/__init__.py` 中导出（可选）

## 常见模式

### 批量处理模式
```python
while True:
    batch = await self._fetch_batch(500)
    if not batch:
        break
    for item in batch:
        await self._process_one(item)
    await self.db.commit()
```

### 查询-处理-更新模式
```python
result = await self.db.execute(select(Model).where(...))
items = result.all()
for item in items:
    result = await self._compute(item)
    await self.db.execute(
        update(Model).where(Model.id == item.id).values(result=result)
    )
await self.db.commit()
```

### 错误恢复模式
```python
try:
    await self._process_one(item)
except Exception as e:
    logger.error(f"处理失败 id={item.id}: {e}")
    # 不 raise，继续处理下一条
```
