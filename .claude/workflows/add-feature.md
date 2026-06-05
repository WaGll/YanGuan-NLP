# Workflow: 功能新增

## 描述

为项目添加新功能的标准化工作流。覆盖从需求分析到 PR 提交的完整流程。

## 适用场景

- 新增 API 端点
- 新增前端页面
- 新增 NLP 分析能力
- 新增数据库表

## 工作流步骤

### Phase 1: 需求分析

Agent: Architecture Agent (或主对话)

**检查清单**:
- [ ] 功能是否与项目定位一致？（考研评论分析平台）
- [ ] 是否涉及新依赖？（检查 requirements.txt）
- [ ] 是否影响现有 API 兼容性？
- [ ] 数据从哪里来？（已有表 / 新表 / 外部数据）

**输出**: 简要的 spec（3-5 行描述 + 涉及的层）

### Phase 2: 数据库变更（如需要）

Agent: Backend Agent

1. 创建/修改 ORM 模型（参考 `templates/sqlalchemy-model.md`）
2. 在 `models/__init__.py` 中注册
3. 更新 `memory/database-schema.md`
4. 如果改动了现有表，考虑 Alembic 迁移

### Phase 3: Service 层实现

Agent: Backend Agent 或 NLP Agent

1. 创建 Service 类（参考 `templates/nlp-service.md`）
2. 实现核心业务逻辑
3. 编写该 Service 的单元测试

### Phase 4: API 端点

Agent: Backend Agent

1. 创建 API 路由文件（参考 `templates/api-endpoint.md`）
2. 在 `main.py` 中注册路由
3. 编写 API 集成测试（参考 `templates/pytest-test.md`）
4. 运行 `pytest tests/test_api/test_xxx.py -v` 验证

### Phase 5: Schema 定义

Agent: Backend Agent

1. 在 `schemas/` 中创建 Pydantic 模型
2. 为 API 响应定义 `response_model`

### Phase 6: 前端页面（如需要）

Agent: Frontend Agent + Visualization Agent

1. 创建 API 客户端模块 `api/xxx.ts`
2. 创建 TypeScript 类型定义 `types/xxx.ts`
3. 创建 Pinia Store（如需状态管理）
4. 创建页面组件（参考 `templates/vue-page.md`）
5. 创建图表组件（如需，参考 `agents/visualization-agent.md`）
6. 在 `router/index.ts` 中添加路由
7. 在 `AppSidebar.vue` 中添加导航

### Phase 7: 集成验证

Agent: QA Agent

```bash
# 后端
cd backend
ruff check app/ && mypy app/ && pytest tests/ -v --cov

# 前端
cd frontend
pnpm vue-tsc --noEmit && pnpm build
```

### Phase 8: 文档更新

Agent: Documentation Agent

- [ ] 更新 `README.md`（功能列表、API 文档链接）
- [ ] 更新 `CLAUDE.md`（如有架构变更）
- [ ] 更新 `memory/roadmap.md`（标记功能完成）
- [ ] 如果是重大架构变更，添加新的 ADR

### Phase 9: 提交

```bash
git add -A
git commit -m "feat: {{功能简短描述}}

- {{变更项1}}
- {{变更项2}}

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

## Agent 交接点

每完成一个 Phase，Agent 应该：
1. 确认本 Phase 的输出文件列表
2. 运行该 Phase 的验证命令
3. 简要汇报完成状态（≤500 字符）
4. 将上下文传递给下一个 Agent Focus
