# YanGuan-NLP（研观）— Claude Code 项目主入口

## 项目定位

研观 (YanGuan-NLP) — 基于 NLP 的考研评论多维度分析平台。
针对 Bilibili 考研相关视频评论（**应用统计学**方向），
提供情感分析、主题建模（LDA + BERTopic 双引擎）、关键词共现网络、趋势分析与实时预测。
面向数据分析/商业分析求职场景的作品集项目。

## 快速导航

| 需要什么 | 去哪里 |
|---------|--------|
| 架构决策 | [memory/architecture-decisions.md](memory/architecture-decisions.md) |
| 编码规范 | [memory/coding-standards.md](memory/coding-standards.md) |
| 已知 Bug | [memory/bug-patterns.md](memory/bug-patterns.md) |
| 数据库 Schema | [memory/database-schema.md](memory/database-schema.md) |
| 技术栈理由 | [memory/tech-stack-rationale.md](memory/tech-stack-rationale.md) |
| 路线图 | [memory/roadmap.md](memory/roadmap.md) |
| Agent 定义 | [agents/](agents/) |
| 代码模板 | [templates/](templates/) |
| 工作流 | [workflows/](workflows/) |
| 可用技能 | [skills/](skills/) |

## 技术栈速查

| 层级 | 技术 | 关键约定 |
|------|------|---------|
| **后端** | FastAPI + SQLAlchemy async + SQLite (aiosqlite, WAL) | Python ≥3.12, Pydantic v2 |
| **NLP** | jieba + SnowNLP + scikit-learn + Gensim LDA + BERTopic + networkx | Pipeline 防泄漏 |
| **LLM** | Ollama (qwen3:4b) + httpx | 批量标注 + 缓存 + 置信度 v2 |
| **前端** | Vue3 + Vite + TypeScript + Element Plus + ECharts + Pinia | 按需引入, Store 架构 |
| **Infra** | Docker Compose + GitHub Actions CI | Ruff + Mypy strict + pytest |

## 架构速览

```
CSV (5961条) → DataLoaderService → SQLite (WAL)
                                        ↓
         ┌──────────────────────────────┴──────────────────────────────┐
         │                Service Layer (13 services)                   │
         │  Cleaner → Aggregation → Keyword → Topic(LDA+BERTopic)      │
         │  Sentiment → TopicSentiment → Trend → Network → Predictor    │
         │  Coherence → LLMLabeler                                      │
         └──────────────────────────────┬──────────────────────────────┘
                                        ↓
         ┌──────────────────────────────┴──────────────────────────────┐
         │                API Layer (23 endpoints, 10 routers)          │
         │  /dashboard  /sentiment  /keywords  /topics  /topic-sentiment│
         │  /trends  /network  /predict  /emotes                       │
         │  /aggregation/*  /coherence/*  /llm/*                       │
         └──────────────────────────────┬──────────────────────────────┘
                                        ↓
         ┌──────────────────────────────┴──────────────────────────────┐
         │              Frontend (9 views, 8 charts)                    │
         │  Dashboard · Sentiment · Topics · TopicSentiment            │
         │  Trends · Network · NetworkAnalytics · Predict · Emotes     │
         └─────────────────────────────────────────────────────────────┘
```

## 开发规范

### 必须遵守 (MUST)

- **async/await**: 所有 FastAPI 端点和 Service 方法
- **Type hints**: 所有函数签名完整标注
- **Pydantic v2**: `model_validate()` / `model_dump()` — 不用 v1 的 `parse_obj()` / `dict()`
- **pathlib.Path**: 所有文件操作，不用 `os.path`
- **APIResponse**: 所有响应包裹在 `APIResponse(data=...)` 中
- **Service 模式**: `__init__(self, db: AsyncSession)` + `Depends(get_db)` 注入

### 禁止操作 (MUST NOT)

| 禁止 | 原因 | 正确做法 |
|------|------|---------|
| 中文 `\b` 正则 | Python `\b` 对中文无效 | `str.replace()` |
| TF-IDF 在 Pipeline 外 fit | 数据泄漏 | `Pipeline([TfidfVectorizer, Classifier])` |
| `generate_from_text()` | 内部重新分词 | `generate_from_frequencies(freq_dict)` |
| CSV 指定 `usecols` | 丢弃时间等列 | 读取全部列 |
| 本地定义 `Base` 类 | 模型注册冲突 | 从 `app.models.base` 导入 |

### 测试规范

- 提交前运行 `pytest tests/ -v --cov=app`
- 覆盖率目标 ≥80%，核心 Service ≥90%
- 集成测试使用内存 SQLite (`sqlite+aiosqlite:///:memory:`)
- API 测试覆盖 4 种状态：正常(200)、空数据、参数错误(422)、不存在(404)

## 常用命令

```bash
# === 后端 Backend ===
cd backend
uvicorn app.main:app --reload --port 3001  # 启动开发服务器 (port 3001)
python scripts/run_pipeline.py             # 导入数据 + 运行 NLP 全管道 (11 steps)
python scripts/run_pipeline.py --progress  # 带进度条
python scripts/run_pipeline.py --skip-bertopic  # 跳过 BERTopic
pytest tests/ -v --cov=app                 # 运行测试 + 覆盖率
ruff check app/ && mypy app/               # 代码检查

# === 前端 Frontend ===
cd frontend
pnpm install && pnpm dev                    # 启动开发服务器 (port 3000)
pnpm build                                  # 生产构建
pnpm vue-tsc --noEmit                       # TypeScript 检查

# === Docker ===
docker-compose up -d                        # 全栈启动
docker-compose logs -f backend              # 查看后端日志
docker compose exec backend python scripts/run_pipeline.py  # 容器内导入数据
```

## 关键文件索引

| 文件 | 用途 |
|------|------|
| `backend/app/main.py` | FastAPI 入口 + lifespan + 10 路由注册 |
| `backend/app/config.py` | Settings (GC_ 前缀环境变量, Ollama, 聚合, 缓存) |
| `backend/app/database.py` | async engine + WAL + get_db |
| `backend/app/models/base.py` | Base + TimestampMixin |
| `backend/app/api/deps.py` | get_db 依赖注入 |
| `backend/app/schemas/common.py` | APIResponse, PaginatedResponse |
| `backend/app/utils/chinese.py` | clean_chinese_text |
| `backend/app/utils/resources.py` | NLPResources 单例 |
| `backend/app/services/llm_labeler.py` | LLMLabeler v2 (批量 + 缓存 + 置信度 v2) |
| `backend/app/services/coherence.py` | CoherenceService (双轨对比 + 混合主题) |
| `backend/app/services/aggregation.py` | AggregationService (视频+时间窗口聚合) |
| `backend/scripts/run_pipeline.py` | 全管道入口 (11 步骤) |
| `frontend/src/router/index.ts` | 10 条路由配置 |
| `.github/workflows/ci.yml` | CI 流水线 |

## 标准工作流

### 新增 API 端点
1. 创建/更新 `schemas/xxx.py`（Pydantic 模型）
2. 创建/更新 `services/xxx.py`（业务逻辑）
3. 创建 `api/xxx.py`（路由，参考 `templates/api-endpoint.md`）
4. 在 `main.py` 中注册路由
5. 编写测试 `tests/test_api/test_xxx.py`

### 新增前端页面
1. 创建 `types/xxx.ts`（类型定义）
2. 创建 `api/xxx.ts`（API 模块）
3. 创建 `stores/xxx.ts`（Pinia store）
4. 创建 `views/XxxView.vue`（参考 `templates/vue-page.md`）
5. 在 `router/index.ts` 添加路由
6. 在 `AppSidebar.vue` 添加导航项

### 修复 Bug
1. 对照 `memory/bug-patterns.md` 检查是否已知模式
2. 先写失败测试（TDD）
3. 修复代码
4. 运行全量测试确保无回归
5. 记录新 Bug 模式到 `memory/bug-patterns.md`

## Agent Teams

本项目配置了 6 个专业化 Agent，定义在 `agents/` 目录：

| Agent | 文件 | 专长领域 |
|-------|------|---------|
| Backend | `agents/backend-agent.md` | FastAPI, SQLAlchemy, API 路由, Service 层 |
| Frontend | `agents/frontend-agent.md` | Vue3, Router, Pinia, API 客户端 |
| NLP | `agents/nlp-agent.md` | jieba, SnowNLP, scikit-learn, Gensim, BERTopic, networkx |
| Visualization | `agents/visualization-agent.md` | ECharts 组件, 响应式, 按需引入 |
| QA | `agents/qa-agent.md` | pytest, coverage, CI, 内存数据库测试 |
| Documentation | `agents/documentation-agent.md` | README, ADR, API 文档, 数据字典 |
