# 长期路线图

## v1.0.0 — MVP (已完成 ✅)

**交付日期**: 2026-06-02

- [x] FastAPI 后端骨架 + 10 个 API 端点
- [x] SQLite 数据库 + 11 表 ORM 模型
- [x] CSV 数据导入管道 (5,961 条评论)
- [x] 中文文本清洗 + jieba 分词 + Bigram
- [x] SnowNLP 情感分析 + ML 分类 (SVM/RF/LR)
- [x] TF-IDF 关键词提取
- [x] LDA 主题建模 (自动 k 选择, c_v coherence)
- [x] 关键词共现网络 + 中心性 + 社区检测
- [x] 主题×情感联合分析
- [x] 时间趋势分析
- [x] 单条评论实时预测 API
- [x] Vue3 前端 9 页面 + 8 ECharts 图表
- [x] Docker + docker-compose 部署
- [x] GitHub Actions CI (Ruff + Mypy + pytest)
- [x] pytest 测试基础框架
- [x] Git 初始化 + MIT License + README

## v1.1.0 — NLP 增强 (已完成 ✅)

**交付日期**: 2026-06-06

### 主题建模增强
- [x] BERTopic 集成 (UMAP + HDBSCAN, diversity + NPMI 评估)
- [x] 短文本聚合 (视频+时间窗口, 缓解短评论语义稀疏)
- [x] LDA 自动 k 选择 (min_k=4, max_k=15, c_v + 均衡性惩罚)
- [x] 主题标签自动生成 (TopicLabelGenerator, 20 个考研领域)
- [x] LLM 主题命名增强 (Ollama qwen3:4b, 批量标注 + 缓存 + 置信度 v2)

### Coherence 评估
- [x] 双轨 Coherence 对比 (LDA vs BERTopic)
- [x] 逐评论 Coherence 评估
- [x] 混合主题检测
- [x] CoherenceSummary API

### API 扩展
- [x] 聚合管理 (4 端点: run/status/config GET/PUT)
- [x] Coherence 评估 (5 端点: compare/per-comment/mixed-topics/summary)
- [x] LLM 标签管理 (4 端点: relabel/cache stats/cache clear/health)
- [x] 总端点数: 10 → 23

### 测试
- [x] 测试覆盖率: 58 → 105 tests
- [x] LLMLabeler 单元测试 (21 tests)
- [x] CoherenceService 单元测试 (7 tests)
- [x] 聚合/Coherence/LLM API 集成测试 (18 tests)

### 清理
- [x] 删除冗余脚本 (scripts/seed_db.py)
- [x] 清理过期 bytecode 和空文件
- [x] 更新项目名引用 (GradCareer → YanGuan-NLP)

## v1.2.0 — 功能扩展 (计划中)

**目标日期**: 2026 Q3

### 分析功能增强
- [ ] 情感分析校准（用人工标注 200 条数据 fine-tune）
- [ ] 趋势预测（Prophet 或 ARIMA）
- [ ] 评论质量评分（垃圾评论过滤）
- [ ] 跨视频对比分析
- [ ] 自定义分析报告导出（PDF/Markdown）

### 前端增强
- [ ] 前端全局 CSS 变量和暗色模式
- [ ] 交互式数据探索（下钻、筛选、排序）
- [ ] 数据导出功能（CSV/Excel）
- [ ] 移动端适配

### LLM 优化
- [ ] LLM 响应速度优化（非 thinking 模型或参数调优）
- [ ] 主题一致性反馈闭环（Coherence → LLM 重标注）
- [ ] 代表性评论质量提升

### 基础设施
- [ ] 数据缓存层（Redis）
- [ ] API 限流 (slowapi)
- [ ] 结构化日志 (structlog)

## v2.0.0 — 平台化

**目标日期**: 2027 H1

### 架构升级
- [ ] PostgreSQL 替代 SQLite
- [ ] 用户认证与权限管理 (JWT + OAuth2)
- [ ] 多项目管理
- [ ] API v2 版本化
- [ ] 数据管道编排（Airflow 或 Prefect）

### AI 能力
- [ ] BERT/RoBERTa 中文预训练模型集成
- [ ] 评论自动摘要生成
- [ ] 情感原因分析（Aspect-Based Sentiment Analysis）
- [ ] 智能问答（基于评论数据的 RAG）

### 产品化
- [ ] 用户管理后台
- [ ] 数据源管理
- [ ] 定时任务调度
- [ ] 分析报告自动生成

## 优先排序原则

1. **作品集价值 > 技术复杂度**: 优先做能展示的功能
2. **数据驱动**: 有数据支撑的功能优先
3. **用户可见 > 内部优化**: 前端展示优先于后端重构
4. **可演示 > 规模化**: MVP 阶段追求可演示，v2.0 追求可扩展

## 技术债务追踪

| 债务项 | 优先级 | 计划版本 |
|--------|--------|---------|
| LLM thinking 模式慢 (qwen3:4b) | 中 | v1.2 |
| LDA k=15 偏高需调整 | 中 | v1.2 |
| SnowNLP 领域漂移 | 中 | v1.2 |
| 前端暗色模式 | 低 | v1.2 |
| 无 API 版本化 | 低 | v2.0 |
| 无用户认证 | 低 | v2.0 |
| SQLite → PostgreSQL | 低 | v2.0 |
