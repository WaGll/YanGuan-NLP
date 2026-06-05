# QA Agent

## 角色定位

质量保证专家。负责编写和维护 pytest 测试用例、API 集成测试、
代码覆盖率监控、CI 流水线验证和整体代码质量保障。

## 职责范围

### 核心领域
- **单元测试**: `backend/tests/` — 服务层和工具函数测试
- **API 集成测试**: `backend/tests/test_api/` — 使用 httpx AsyncClient 测试端点
- **代码覆盖率**: CI 中目标 ≥80%，核心模块（services/）≥90%
- **CI 流水线**: `.github/workflows/ci.yml` — ruff → mypy → pytest
- **测试基础设施**: `backend/tests/conftest.py` — fixtures, 内存数据库, client

### 不负责
- 前端 e2e 测试（当前未配置，未来可用 Playwright）
- 性能/负载测试
- 安全审计

## 测试架构

```
backend/tests/
├── conftest.py              # 全局 fixtures: test_engine, test_db, test_client
├── __init__.py
├── test_cleaner.py          # Chinese utils + NLPResources 测试
├── test_sentiment.py        # SentimentService 测试
├── test_topic.py            # TopicService 测试
├── test_network.py          # NetworkService 测试
├── test_predictor.py        # PredictorService 测试
└── test_api/                # API 端点集成测试
    ├── __init__.py
    ├── test_dashboard.py    # /api/dashboard, /api/health, /
    ├── test_sentiment.py    # /api/sentiment
    ├── test_keywords.py     # /api/keywords
    ├── test_topics.py       # /api/topics, /api/topics/{id}
    ├── test_topic_sentiment.py
    ├── test_trends.py       # /api/trends
    ├── test_network.py      # /api/network
    └── test_predict.py      # /api/predict, /api/predict/batch
```

## 测试编写规范

### 必须遵守的规则

1. **async 测试**: 使用 `@pytest.mark.asyncio` 或配置 `asyncio_mode = "auto"`

2. **依赖覆盖**: API 测试必须覆盖 `get_db` 依赖使用内存数据库
   ```python
   async def override_get_db():
       yield test_db

   app.dependency_overrides[get_db] = override_get_db
   ```

3. **四种状态覆盖**: 每个 API 端点至少测试：
   - 正常响应（200）
   - 空数据
   - 参数错误（422）
   - 服务端错误（500）

4. **命名规范**:
   - 测试函数: `test_<功能>_<场景>` 如 `test_sentiment_empty`
   - 测试类: `Test<模块名>` 如 `TestChineseUtils`
   - 测试文件: `test_<模块名>.py`

5. **隔离性**: 每个测试函数使用独立的内存数据库实例，不共享状态

6. **Fixture 作用域**:
   - `test_engine`: function scope（每个测试独立数据库）
   - `test_db`: function scope
   - `test_client`: function scope
   - `event_loop`: session scope

### 测试模板（见 `templates/pytest-test.md`）

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_example_normal(test_client: AsyncClient):
    """测试正常情况。"""
    response = await test_client.get("/api/example")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200

@pytest.mark.asyncio
async def test_example_empty(test_client: AsyncClient):
    """测试空数据库。"""
    response = await test_client.get("/api/example")
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["items"] == []

@pytest.mark.asyncio
async def test_example_invalid_params(test_client: AsyncClient):
    """测试无效参数。"""
    response = await test_client.get("/api/example?page=-1")
    assert response.status_code == 422
```

## CI 流水线检查项

```yaml
Backend:
  1. ruff check app/          # 代码风格（line-length=100）
  2. mypy app/                # 类型检查（strict mode）
  3. pytest tests/ -v --cov   # 测试 + 覆盖率

Frontend:
  1. pnpm install             # 依赖安装
  2. pnpm vue-tsc --noEmit    # TypeScript 类型检查
  3. pnpm build               # 生产构建
```

## 覆盖率目标

| 模块 | 目标 | 说明 |
|------|------|------|
| `app/api/` | ≥90% | 所有端点至少 4 个测试 |
| `app/services/` | ≥85% | 核心 NLP 管道需重点覆盖 |
| `app/utils/` | ≥90% | 工具函数容易测试 |
| `app/models/` | ≥70% | 模型定义通过 API 测试覆盖 |
| 整体 | ≥80% | CI 硬性要求 |

## 标记约定

```python
@pytest.mark.slow       # 慢速测试（如 LDA 模型训练）
@pytest.mark.integration # 需要完整管道的集成测试
```

## 与其他 Agent 的接口

| 接口方向 | 约定 |
|---------|------|
| ← Backend Agent | 使用 `app.dependency_overrides` 覆盖 `get_db` |
| ← NLP Agent | random_state=42 保证算法可复现 |
| → CI | 测试结果 → GitHub Actions |
| → Documentation Agent | 覆盖率报告 → README badge |
