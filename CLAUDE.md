# YanGuan-NLP（研观）

> 📁 详细指令见 [.claude/CLAUDE.md](.claude/CLAUDE.md) | ADR 见 [memory/](.claude/memory/) | 模板见 [templates/](.claude/templates/)

## 项目定位

研观 (YanGuan-NLP) — 基于 NLP 的考研评论多维度分析平台。
B 站考研评论 → 情感分析、主题建模、关键词网络、趋势分析与实时预测。
面向数据分析/商业分析求职的作品集项目。

## 技术栈

- **Backend**: FastAPI + SQLAlchemy async + SQLite (aiosqlite, WAL) + Pydantic v2
- **NLP**: jieba + SnowNLP + scikit-learn (Pipeline) + Gensim LDA + networkx
- **Frontend**: Vue3 + Vite + TypeScript + Element Plus + ECharts + Pinia
- **Infra**: Docker Compose + GitHub Actions CI

## 架构

```
CSV → DataLoaderService → SQLite → API (10 endpoints) → Pinia → ECharts (8 charts)
```

- `backend/app/api/` — 薄路由（验证 → 调用 service → 返回 JSON）
- `backend/app/services/` — 业务逻辑（10 个 Service 类）
- `backend/app/models/` — 11 个 SQLAlchemy ORM 模型
- `frontend/src/views/` — 9 个页面 + 8 个 Pinia stores

## 开发规范

### 必须遵守

- **async/await**: 所有端点和 Service 方法必须是 async
- **Type hints**: 所有函数签名必须有完整类型标注
- **Pydantic v2**: `model_validate` / `model_dump`（不用 v1 API）
- **pathlib.Path**: 所有文件操作
- **APIResponse 包装**: 所有响应使用 `APIResponse(data=...)`
- **Service 构造**: `__init__(self, db: AsyncSession)` 接受 Depends 注入

### 禁止操作

- ❌ 中文正则 `\b` → 用 `str.replace()`
- ❌ TF-IDF 在 split 前 fit → 用 `sklearn.pipeline.Pipeline`
- ❌ WordCloud `generate_from_text()` → 用 `generate_from_frequencies()`
- ❌ CSV 丢弃时间列 → 读取全部 11 列
- ❌ 本地重定义 `Base` → 从 `app.models.base` 导入

### 测试

- `pytest` 提交前必跑，覆盖率 ≥80%
- `pytest-asyncio` + `asyncio_mode = "auto"`
- 集成测试使用内存 SQLite (`sqlite+aiosqlite:///:memory:`)

## 常用命令

```bash
# 一键启动
./start.sh                                        # 同时启动前后端 (port 3000+3001)

# 后端
cd backend && uvicorn app.main:app --reload --port 3001     # 启动 API (port 3001)
cd backend && python scripts/run_pipeline.py                # 导入数据 + 运行 NLP 管道
cd backend && python scripts/run_pipeline.py --progress     # 启用进度条
cd backend && pytest tests/ -v --cov=app                    # 测试 + 覆盖率
cd backend && ruff check app/ && mypy app/                  # 代码检查

# 前端
cd frontend && pnpm dev                                     # 启动开发服务器 (port 3000)
cd frontend && pnpm build                                   # 生产构建
cd frontend && pnpm vue-tsc --noEmit                        # TypeScript 检查

# Docker
docker-compose up -d                              # 全栈启动
```

## Agent Teams

| Agent | 职责 | 定义文件 |
|-------|------|---------|
| Backend | FastAPI + ORM + API + Services | `agents/backend-agent.md` |
| Frontend | Vue3 + Router + Pages + Stores | `agents/frontend-agent.md` |
| NLP | 分词 + 情感 + 主题 + 网络 + 预测 | `agents/nlp-agent.md` |
| Visualization | ECharts 图表（8 个） | `agents/visualization-agent.md` |
| QA | pytest + coverage + CI | `agents/qa-agent.md` |
| Documentation | README + ADR + 数据字典 | `agents/documentation-agent.md` |
