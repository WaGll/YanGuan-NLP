# Workflow: Bug 修复

## 描述

标准化的 Bug 修复流程。确保修复不会引入新问题。

## 适用场景

- 用户报告的 Bug
- CI 中发现的测试失败
- 代码审查中发现的问题

## 工作流步骤

### Phase 1: Bug 诊断

Agent: 相关领域 Agent

1. **复现 Bug**: 在本地环境中重现问题
2. **定位根因**: 找到出错的代码文件和行号
3. **检查已知 Bug 模式**: 对照 `memory/bug-patterns.md` 中的 7 个已知模式
4. **评估影响范围**:
   - 哪些 API 端点受影响？
   - 哪些前端页面受影响？
   - 是否有数据库数据损坏？

**输出**: Bug 诊断报告
```
Bug: [简短描述]
位置: [文件:行号]
根因: [1-2 句话]
影响: [受影响的端点/页面]
模式匹配: [是否匹配已知 Bug 模式]
```

### Phase 2: 编写失败的测试

Agent: QA Agent

**原则**: 先写失败的测试，再修复代码（TDD）。

1. 编写能复现 Bug 的测试用例
2. 运行测试确认失败
```bash
cd backend && pytest tests/test_xxx.py -v -k "test_bug_description"
```

### Phase 3: 实施修复

Agent: 相关领域 Agent

1. 修改代码
2. 遵循项目编码规范（`memory/coding-standards.md`）
3. 检查是否引入其他已知 Bug 模式（`memory/bug-patterns.md`）

### Phase 4: 验证修复

Agent: QA Agent

```bash
# 4.1 确认之前的失败测试通过
cd backend && pytest tests/test_xxx.py -v -k "test_bug_description"

# 4.2 运行全量测试确保无回归
cd backend && pytest tests/ -v

# 4.3 代码检查
cd backend && ruff check app/ && mypy app/
cd frontend && pnpm vue-tsc --noEmit
```

### Phase 5: 记录 Bug

Agent: Documentation Agent

1. 将 Bug 添加到 `memory/bug-patterns.md`（如果模式是新的）
2. 确保文档中包含：
   - 错误代码和正确代码的对比
   - 根因分析
   - 防范措施

### Phase 6: 提交

```bash
git add -A
git commit -m "fix: {{Bug 简短描述}}

根因: {{1-2 句话}}
修复: {{修复方式}}

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

## Bug 严重度分级

| 级别 | 描述 | 响应要求 |
|------|------|---------|
| **P0-阻塞** | 应用无法启动、数据库损坏 | 立即修复，不允许其他更改 |
| **P1-严重** | 核心功能错误、数据计算错误 | 优先修复，可包含在同一 PR |
| **P2-中等** | UI 显示错误、非核心功能异常 | 计划修复，下个版本 |
| **P3-轻微** | 代码风格、注释缺失、typo | 顺手修复 |

## 已知 Bug 模式速查

从 `memory/bug-patterns.md` 摘录：

1. 中文 `\b` regex → `str.replace()`
2. TF-IDF 泄漏 → `Pipeline`
3. WordCloud 频率 → `generate_from_frequencies()`
4. 1D 聚类 → `KBinsDiscretizer`
5. CSV 时间列丢弃 → 读取全部列
6. temp.csv 竞态 → 流式读取
7. `min`/`max` 遮蔽 → 重命名变量
