# YanGuan-NLP

> 基于 NLP 的考研评论多维度分析平台
> Bilibili Postgraduate Exam Comment Analysis with NLP

[![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python)](https://www.python.org/) [![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688?logo=fastapi)](https://fastapi.tiangolo.com/) [![Vue](https://img.shields.io/badge/Vue-3.x-4FC08D?logo=vue.js)](https://vuejs.org/) [![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?logo=typescript)](https://www.typescriptlang.org/) [![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://www.docker.com/) [![CI](https://img.shields.io/badge/CI-GitHub_Actions-2088FF?logo=githubactions)](https://github.com/features/actions)

---

## 项目简介

**YanGuan-NLP** 是一个的 NLP 作品集项目。针对 B 站考研相关视频的 5,961 条评论，提供情感分析、主题建模（LDA + BERTopic 双引擎）、关键词共现网络、趋势分析、实时预测，以及短文本聚合、双轨 Coherence 评估和 LLM 主题命名增强。

### 核心亮点

- 🔌 **23 个 REST API** — FastAPI 异步端点，统一 `APIResponse<T>` 响应格式
- 📊 **9 个可视化页面** — Vue3 + ECharts，从仪表盘到实时预测全覆盖
- 🧠 **双引擎主题建模** — Gensim LDA + BERTopic，自动 k 选择 + Grid Search
- 🤖 **LLM 增强** — Ollama (qwen3:4b) 批量主题命名 + 内存缓存
- 📏 **双轨 Coherence** — LDA vs BERTopic 一致性对比 + 逐评论评估 + 混合主题检测
- 🔗 **短文本聚合** — 视频+时间窗口聚合缓解短评论语义稀疏
- 🐳 **一键部署** — Docker Compose 前后端编排，GitHub Actions CI
- 🏗️ **企业级架构** — Service 层分离、Pydantic v2、Pinia 状态管理、TypeScript 全链路

---

## 系统架构

```
CSV (5961 条) → DataLoaderService → SQLite (WAL)
                                        ↓
         ┌──────────────────────────────┴──────────────────────────────┐
         │              Service Layer (13 services)                     │
         │  DataLoader · Cleaner · Aggregation · Keyword               │
         │  Topic(LDA+BERTopic) · Sentiment · TopicSentiment           │
         │  Trend · Network · Predictor · Coherence · LLMLabeler       │
         └──────────────────────────────┬──────────────────────────────┘
                                        ↓
         ┌──────────────────────────────┴──────────────────────────────┐
         │              API Layer (23 endpoints, 10 routers)            │
         │  /dashboard · /sentiment · /keywords · /topics             │
         │  /topic-sentiment · /trends · /network · /predict          │
         │  /emotes · /aggregation · /coherence · /llm                │
         └──────────────────────────────┬──────────────────────────────┘
                                        ↓
         ┌──────────────────────────────┴──────────────────────────────┐
         │        Frontend (9 views, 8 charts, 7 Pinia stores)         │
         │  Dashboard · Sentiment · Topics · TopicSentiment            │
         │  Trends · Network · Predict · NetworkAnalytics · Emotes     │
         └─────────────────────────────────────────────────────────────┘
```

---

## 技术栈

| 层级               | 技术                                       | 关键约定                       |
| ------------------ | ------------------------------------------ | ------------------------------ |
| **后端框架** | FastAPI + Uvicorn                          | async/await 全链路             |
| **ORM + DB** | SQLAlchemy async + SQLite (aiosqlite, WAL) | Depends(get_db) 注入           |
| **数据验证** | Pydantic v2 + pydantic-settings            | model_validate / model_dump    |
| **中文分词** | jieba + 自定义词典 + 同义词归一化          | NLPResources 单例              |
| **情感分析** | SnowNLP + scikit-learn (Pipeline 防泄漏)   | SVM + RF + LR                  |
| **主题建模** | Gensim LDA + BERTopic + UMAP + HDBSCAN     | 自动 k + Grid Search           |
| **语义网络** | networkx + 3 种中心性 + Louvain 社区检测   | 共现窗口=5                     |
| **LLM 集成** | Ollama (qwen3:4b) + httpx AsyncClient      | 批量标注 + 缓存                |
| **前端框架** | Vue3 + Vite + TypeScript                   | Composition API                |
| **UI 组件**  | Element Plus + ECharts 5.6                 | 按需引入                       |
| **状态管理** | Pinia 2.3                                  | store 按页面拆分               |
| **容器化**   | Docker Compose                             | 后端:3001 / 前端:3000          |
| **CI/CD**    | GitHub Actions                             | Ruff + Mypy + pytest + vue-tsc |

---

## 快速开始

### 前置要求

- Python ≥ 3.12
- Node.js ≥ 18 (推荐 22+)
- pnpm ≥ 9
- [Ollama](https://ollama.com/) (可选，LLM 主题命名需要)
- Docker ≥ 24.0 (可选)

### 一键启动

```bash
./start.sh          # 同时启动前后端 (port 3000 + 3001)
```

### 本地开发

```bash
# 后端
cd backend
pip install -r requirements.txt
python scripts/run_pipeline.py          # 导入数据 + 运行 NLP 全管道
uvicorn app.main:app --reload --port 3001  # API → http://localhost:3001

# 前端（新终端）
cd frontend
pnpm install && pnpm dev                # → http://localhost:3000
```

### Docker 部署

```bash
docker-compose up -d
# 后端: http://localhost:3001
# 前端: http://localhost:3000
# API 文档: http://localhost:3001/docs
```

### 管道选项

```bash
python scripts/run_pipeline.py --progress           # 带进度条
python scripts/run_pipeline.py --skip-bertopic      # 跳过 BERTopic (加速)
python scripts/run_pipeline.py --force-reprocess    # 强制重新清洗
python scripts/run_pipeline.py --csv data/xxx.csv   # 自定义 CSV 源文件
```

---

## API 端点

启动后端后访问 Swagger 文档: http://localhost:3001/docs

### 核心分析 (10 端点)

| 方法 | 端点                     | 功能                                 |
| ---- | ------------------------ | ------------------------------------ |
| GET  | `/api/health`          | 健康检查                             |
| GET  | `/api/dashboard`       | 数据总览（评论数、用户数、情感均值） |
| GET  | `/api/sentiment`       | 情感分布 + ML 模型准确率             |
| GET  | `/api/keywords`        | 关键词列表 + 词云数据                |
| GET  | `/api/topics`          | 主题列表（支持 method=lda/bertopic） |
| GET  | `/api/topic-sentiment` | 主题×情感 联合分布矩阵              |
| GET  | `/api/trends`          | 情感/关键词/主题时序趋势             |
| GET  | `/api/network`         | 共现网络节点 + 边 + 中心性           |
| GET  | `/api/emotes`          | 表情分析 + 情感关联 + 词云           |
| POST | `/api/predict`         | 单条评论实时预测                     |
| POST | `/api/predict/batch`   | 批量评论预测                         |

### 聚合管理 (4 端点)

| 方法 | 端点                        | 功能                               |
| ---- | --------------------------- | ---------------------------------- |
| POST | `/api/aggregation/run`    | 触发重新聚合                       |
| GET  | `/api/aggregation/status` | 聚合状态统计（组数、覆盖率、分布） |
| GET  | `/api/aggregation/config` | 当前聚合配置                       |
| PUT  | `/api/aggregation/config` | 运行时更新配置                     |

### Coherence 评估 (5 端点)

| 方法 | 端点                                | 功能                     |
| ---- | ----------------------------------- | ------------------------ |
| GET  | `/api/coherence/compare`          | LDA vs BERTopic 双轨对比 |
| GET  | `/api/coherence/per-comment`      | 逐评论 coherence（分页） |
| GET  | `/api/coherence/per-comment/{id}` | 单条评论 coherence 详情  |
| GET  | `/api/coherence/mixed-topics`     | 混合主题检测             |
| GET  | `/api/coherence/summary`          | Dashboard coherence 摘要 |

### LLM 管理 (4 端点)

| 方法   | 端点                     | 功能                       |
| ------ | ------------------------ | -------------------------- |
| POST   | `/api/llm/relabel`     | 触发 LLM 重新标注主题      |
| GET    | `/api/llm/health`      | Ollama 健康检查 + 模型信息 |
| GET    | `/api/llm/cache/stats` | LLM 缓存统计               |
| DELETE | `/api/llm/cache`       | 清空 LLM 缓存              |

### 测试预测

```bash
curl -X POST http://localhost:3001/api/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "数学太难了，但是统计学很有意思"}'
```

---

## 项目结构

```text
YanGuan-NLP/
├── backend/
│   ├── app/
│   │   ├── api/              # 10 个 FastAPI 路由模块
│   │   ├── models/           # 11 个 SQLAlchemy ORM 模型
│   │   ├── schemas/          # 13 个 Pydantic Schema 模块
│   │   ├── services/         # 13 个业务逻辑 Service
│   │   ├── utils/            # 中文处理、分词器、NLPResources 单例
│   │   ├── config.py         # Settings (GC_ 前缀环境变量)
│   │   ├── database.py       # async engine + WAL + get_db
│   │   └── main.py           # FastAPI 入口 + 路由注册
│   ├── data/                 # CSV 源数据、停用词、词典、同义词表
│   │   └── model/            # 训练好的 LDA 模型文件
│   ├── scripts/              # 管道脚本 + 工具
│   │   ├── run_pipeline.py   # 完整 NLP 管道 (11 步骤)
│   │   ├── run_bertopic_only.py  # 仅 BERTopic 快速迭代
│   │   ├── analyze_noise.py  # 噪声词分析工具
│   │   └── tokenization_audit.py # 分词质量审计
│   ├── tests/
│   │   ├── test_api/         # API 集成测试 (11 文件)
│   │   └── test_services/    # Service 单元测试 (2 文件)
│   ├── requirements.txt
│   └── pyproject.toml        # Ruff, Mypy, Pytest 配置
├── frontend/
│   └── src/
│       ├── views/            # 9 个 Vue 页面组件
│       ├── stores/           # 7 个 Pinia 状态管理
│       ├── components/
│       │   ├── charts/       # 8 个 ECharts 图表组件
│       │   ├── common/       # StatCard, LoadingCard, TopicCard 等
│       │   └── layout/       # AppHeader, AppSidebar
│       ├── api/              # 10 个 Axios API 模块
│       ├── router/           # Vue Router 4 (10 routes)
│       └── types/            # 12 个 TypeScript 类型文件
├── .claude/                  # Claude Code 项目记忆体系
├── .github/workflows/ci.yml  # GitHub Actions CI
├── start.sh                  # 一键启动脚本
├── docker-compose.yml
├── CLAUDE.md                 # Claude Code 项目入口
├── LICENSE
└── README.md
```

---

## NLP 管道

11 步全自动管道，从原始 CSV 到分析结果：

```
0. NLP 资源加载 (jieba 词典 + 停用词 + 同义词)
1. 数据导入 (CSV → SQLite, 5961 条)
2. 文本清洗 + jieba 分词 + 词性过滤
2.5. 短文本聚合 (video + time window, ~249 组)
3. 关键词词频统计 (1618 词)
4. TF-IDF 计算 (500 词)
5. LDA 主题建模 (自动 k 选择, c_v coherence + 均衡性惩罚)
6. BERTopic 主题建模 (UMAP + HDBSCAN, diversity + NPMI 评估)
7. 共现网络构建 (100 节点, 1743 边, Louvain 社区)
8. 情感分析 (SnowNLP + 3 种 ML 分类器)
9. 主题×情感联合矩阵
10. 趋势分析 (日/周/月/年粒度)
11. 业务洞察报告
```

---

## 数据说明

数据来源: B 站考研相关视频评论 (5,961 条)。

| 字段                  | 类型   | 说明                 |
| --------------------- | ------ | -------------------- |
| `comment_id`        | bigint | B 站评论唯一标识     |
| `parent_comment_id` | bigint | 父评论 ID (0 = 顶级) |
| `create_time`       | int    | Unix 时间戳          |
| `video_id`          | bigint | B 站视频标识         |
| `content`           | text   | 评论原文             |
| `user_id`           | bigint | 用户唯一标识         |
| `nickname`          | text   | 用户昵称             |
| `sub_comment_count` | int    | 子评论数             |

NLP 衍生字段: `cleaned_content`, `tokens_json`, `bigram_tokens_json`, `token_count`

---

## 开发

### 运行测试

```bash
cd backend
pytest tests/ -v --cov=app --cov-report=term-missing
```

### 代码检查

```bash
cd backend && ruff check app/ && mypy app/    # 后端
cd frontend && pnpm vue-tsc --noEmit           # 前端
```

### 常用命令

```bash
# 启动后端 API (dev)
uvicorn app.main:app --reload --port 3001

# 运行 NLP 管道
python scripts/run_pipeline.py --progress

# 仅 BERTopic (快速迭代)
python scripts/run_bertopic_only.py

# 噪声词分析
python scripts/analyze_noise.py
```


## 贡献

开发前请阅读:

- [编码规范](.claude/memory/coding-standards.md)
- [架构决策记录](.claude/memory/architecture-decisions.md)
- [已知 Bug 模式](.claude/memory/bug-patterns.md)

---

## 许可证

[MIT License](LICENSE)

---

**v1.1.0 · 2026-06-06**
