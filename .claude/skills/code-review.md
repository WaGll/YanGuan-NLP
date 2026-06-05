# Skill: code-review

## 描述

按项目标准审查代码变更。检查编码规范、已知 Bug 模式、类型安全、测试覆盖和架构一致性。

## 触发条件

- 用户说"审查代码"、"code review"、"检查这段代码"
- 提交 PR 前
- 新功能开发完成后

## 审查清单

### 1. 编码规范检查

- [ ] 所有端点使用 `async/await`
- [ ] Service 方法使用 `async/await`
- [ ] 响应包裹在 `APIResponse` 中
- [ ] 使用 `pathlib.Path`（非 `os.path`）
- [ ] Pydantic v2 风格: `model_validate`, `model_dump`
- [ ] Type hints 完整
- [ ] 业务逻辑用中文注释
- [ ] 数据库操作使用 SQLAlchemy 2.0 风格 `select()`
- [ ] 批量操作使用 `INSERT OR IGNORE` + 分批

### 2. 已知 Bug 模式检查

- [ ] **中文 `\b` 正则**: 使用 `str.replace()` 而非 regex word boundaries
- [ ] **TF-IDF 泄漏**: 使用 `Pipeline` 包裹 vectorizer + classifier
- [ ] **词云频率**: 使用 `generate_from_frequencies()` 而非 `generate_from_text()`
- [ ] **时间列丢弃**: CSV 读取保留全部 11 列
- [ ] **temp.csv 竞态**: 使用流式读取或直接读原文件
- [ ] **min/max 遮蔽**: 不覆盖内置函数名
- [ ] **Base 重定义**: 从 `app.models.base` 导入，不本地重定义

### 3. 类型安全检查

- [ ] 所有函数参数有类型标注
- [ ] 返回类型明确（不用 `Any` 除非必要）
- [ ] Optional 类型显式标注 `Optional[str]` 而非 `str | None`（虽然等价，保持一致）
- [ ] mypy `--strict` 模式通过

### 4. 测试覆盖检查

- [ ] 新 API 端点至少有 4 个测试（正常、空数据、参数错误、异常）
- [ ] 新 Service 方法有单元测试
- [ ] 测试使用内存 SQLite（不污染真实数据库）
- [ ] 测试函数有描述性名称 `test_<功能>_<场景>`

### 5. 架构一致性检查

- [ ] API 路由只做验证 + 调用 service（不直接在路由写业务逻辑）
- [ ] 数据库模型在 `app/models/` 中
- [ ] 所有模型在 `app/models/__init__.py` 中导入
- [ ] 新 service 接受 `db: AsyncSession` 且不自行创建 session
- [ ] 环境变量使用 `GC_` 前缀

### 6. 前端检查（如涉及）

- [ ] Vue 组件覆盖 loading / error / empty / data 四种状态
- [ ] 页面组件使用懒加载 `() => import(...)`
- [ ] API 调用有 try/catch 错误处理
- [ ] TypeScript 类型定义完整
- [ ] 使用 Element Plus CSS 变量保持主题一致

### 7. 性能检查

- [ ] 批量数据库操作分批（batch_size=500）
- [ ] 大文本处理使用生成器而非一次性加载
- [ ] ECharts 按需引入（非完整包）
- [ ] 网络请求有 loading 状态

## 审查命令

```bash
# 自动检查
cd backend && ruff check app/          # 代码风格
cd backend && mypy app/                # 类型检查
cd backend && pytest tests/ -v --cov   # 测试覆盖
cd frontend && pnpm vue-tsc --noEmit  # 前端类型检查
```

## 审查输出

生成审查报告格式：
```
## Code Review — [文件名/功能名]

### 通过项 ✅
- ...

### 需改进项 ⚠️
- [文件:行号] 问题描述 → 建议修复方式

### 阻塞项 ❌
- [文件:行号] 严重问题 → 必须修复
```
