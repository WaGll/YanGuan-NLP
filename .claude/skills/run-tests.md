# Skill: run-tests

## 描述

运行测试套件并生成覆盖率报告。支持全部测试、单个模块测试、API 测试等不同范围。

## 触发条件

- 用户说"跑测试"、"运行测试"、"检查覆盖率"
- 修改代码后需要验证
- CI 前本地预检

## 执行步骤

### 步骤 1: 全部测试 + 覆盖率

```bash
cd backend && python -m pytest tests/ -v --cov=app --cov-report=term-missing
```

### 步骤 2: 仅单元测试（不含 API 集成测试）

```bash
cd backend && python -m pytest tests/ -v --ignore=tests/test_api
```

### 步骤 3: 仅 API 集成测试

```bash
cd backend && python -m pytest tests/test_api/ -v
```

### 步骤 4: 单个测试文件

```bash
cd backend && python -m pytest tests/test_cleaner.py -v
```

### 步骤 5: 按标记运行

```bash
# 跳过慢速测试
cd backend && python -m pytest tests/ -v -m "not slow"

# 仅慢速测试
cd backend && python -m pytest tests/ -v -m "slow"

# 仅集成测试
cd backend && python -m pytest tests/ -v -m "integration"
```

### 步骤 6: 仅运行失败的测试

```bash
cd backend && python -m pytest tests/ -v --lf
```

### 步骤 7: 代码检查（Ruff + Mypy）

```bash
cd backend && ruff check app/ && mypy app/
```

### 步骤 8: 前端 TypeScript 检查

```bash
cd frontend && pnpm vue-tsc --noEmit
```

## 完整 CI 预检

```bash
# Backend
cd backend
ruff check app/                          # 代码风格
mypy app/                                # 类型检查
pytest tests/ -v --cov=app --cov-report=term-missing  # 测试

# Frontend
cd frontend
pnpm vue-tsc --noEmit                    # TypeScript 检查
pnpm build                               # 生产构建
```

## 覆盖率报告解读

```
Name                          Stmts   Miss  Cover
-------------------------------------------------
app/api/dashboard.py             25      0   100%
app/services/cleaner.py          48      2    96%
...
-------------------------------------------------
TOTAL                           500     50    90%
```

- **Cover < 80%**: CI 失败，必须补充测试
- **Cover 80-90%**: 可接受
- **Cover > 90%**: 优秀

## 测试失败排查

| 症状 | 可能原因 | 解决方案 |
|------|---------|---------|
| `ImportError` | 依赖未安装 | `pip install -r requirements.txt` |
| `NLPResources 尚未加载` | test 中未 mock resources | 确保 test 使用内存数据 |
| `数据库锁` | SQLite 并发问题 | 使用独立内存数据库 fixtures |
| `assert 200 == 422` | API 参数验证变更 | 同步更新测试和 schemas |
| 测试互相影响 | fixture scope 问题 | 使用 function scope fixtures |

## 输出

- 终端显示测试结果（pass/fail/skip）
- 覆盖率报告（term-missing 显示未覆盖行）
- 退出码: 0 = 全部通过, 1 = 有失败
