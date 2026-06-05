# 编码规范

## Python (Backend)

### 代码风格
- **行长度**: 100 字符（Ruff 配置）
- **引号**: 双引号 `"`
- **缩进**: 4 空格
- **导入排序**: isort (Ruff I 规则)
- **Python 版本**: ≥3.12

### async/await
```python
# ✅ 正确: 所有端点使用 async
@router.get("/items")
async def get_items(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Item))
    return APIResponse(data=result.scalars().all())

# ❌ 错误: 同步端点
@router.get("/items")
def get_items(db: Session = Depends(get_db)):  # 不要同步
    ...
```

### Type Hints
```python
# ✅ 完整标注
async def process_comments(
    self, batch_size: int = 500
) -> dict[str, int]:
    ...

# ❌ 缺少标注
async def process_comments(self, batch_size=500):  # 缺少类型
    ...
```

### Pydantic v2
```python
# ✅ Pydantic v2 风格
data = MyModel.model_validate(dict_data)
output = model.model_dump()

# ❌ Pydantic v1 风格（本项目禁止）
data = MyModel.parse_obj(dict_data)
output = model.dict()
```

### 中文注释规范
```python
# ✅ 业务逻辑用中文注释
def classify_sentiment(score: float) -> str:
    """根据 SnowNLP 得分（0~1）映射到情感类别。"""
    # 阈值参考 SnowNLP 官方文档
    if score > 0.6:
        return "positive"       # 积极
    elif score < 0.4:
        return "negative"       # 消极
    return "neutral"            # 中性

# ✅ 技术代码用英文注释
# Use INSERT OR IGNORE to skip duplicates safely
stmt = text(f"INSERT OR IGNORE INTO comments ({col_names}) VALUES ({placeholders})")
```

### 文件操作
```python
# ✅ 使用 pathlib
from pathlib import Path
data_dir = Path("data")
file_path = data_dir / "stopwords.txt"
content = file_path.read_text(encoding="utf-8")

# ❌ 不用 os.path
import os
file_path = os.path.join("data", "stopwords.txt")  # 禁止
```

### 数据库操作
```python
# ✅ SQLAlchemy 2.0 风格
result = await db.execute(
    select(Comment.id, Comment.content)
    .where(Comment.cleaned_content.is_(None))
    .limit(500)
)

# ✅ 批量写入使用原始 SQL
stmt = text("INSERT OR IGNORE INTO comments (...) VALUES (...)")

# ❌ 旧式 query API（SQLAlchemy 1.x）
result = db.query(Comment).filter_by(...)  # 禁止
```

## TypeScript/Vue (Frontend)

### 组件结构
```vue
<script setup lang="ts">
// 1. imports
// 2. props & emits
// 3. composables & stores
// 4. reactive state
// 5. computed
// 6. methods
// 7. lifecycle hooks
</script>

<template>
  <!-- markup -->
</template>

<style scoped>
/* styles */
</style>
```

### 状态管理
```typescript
// 每个数据获取覆盖四种状态
const data = ref<Item[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

// Empty state 由模板中检查 data.length === 0 判断
```

### API 调用
```typescript
// ✅ 使用封装的 API 模块
import { getSentiment } from '@/api/sentiment'

// ❌ 直接使用 axios
import axios from 'axios'
```

### 组件命名
- 页面组件: `XxxView.vue` (PascalCase, View 后缀)
- 图表组件: `XxxChart.vue` (PascalCase, Chart 后缀)
- 通用组件: `XxxCard.vue` / `XxxPanel.vue`
- 布局组件: `AppXxx.vue` (App 前缀)

## 通用规范

### Git 提交
```
<type>: <简短描述>

<详细说明（可选）>

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

Type 类型: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`, `style`

### 环境变量
- 前缀: `GC_`
- 开发环境: `.env` 文件（不提交到 Git）
- 参考: `backend/.env.example`

### 文件编码
- Python: UTF-8
- Vue/TypeScript: UTF-8
- 数据文件: UTF-8 或 GBK（自动检测）
- Git: UTF-8
