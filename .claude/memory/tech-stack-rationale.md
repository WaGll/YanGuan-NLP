# 技术栈选型理由

## Backend: FastAPI

| 对比项 | FastAPI | Flask | Django |
|--------|---------|-------|--------|
| async 支持 | ✅ 原生 | ❌ 需扩展 | ⚠️ 3.1+ |
| 自动文档 | ✅ Swagger | ❌ 需插件 | ⚠️ DRF |
| 类型安全 | ✅ Pydantic | ❌ | ❌ |
| 性能 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| 学习曲线 | 中等 | 低 | 高 |

**选择理由**: 自动生成 API 文档（Swagger UI）适合作品集展示；Pydantic v2 与 SQLAlchemy 完美配合；async 原生支持。

## 数据库: SQLite + aiosqlite

**选择理由**:
- 零配置：不需要安装数据库服务
- 作品集项目：评审者 git clone 后 `pip install` 即可运行
- SQLAlchemy ORM：未来可一键切换 PostgreSQL
- 数据量：3009 条远低于 SQLite 的 TB 级上限

**不选择 MySQL/PostgreSQL 的原因**:
- 需要独立服务，增加部署复杂度
- 对 3000 条数据来说杀鸡用牛刀

## NLP: jieba + SnowNLP + scikit-learn + Gensim

| 库 | 用途 | 替代方案 | 选择理由 |
|-----|------|---------|---------|
| **jieba** | 中文分词 | pkuseg, HanLP | 社区最大，自定义词典方便，速度够快 |
| **SnowNLP** | 情感分析 | transformers | 轻量（无需 GPU），中文原生支持 |
| **scikit-learn** | ML 分类 | XGBoost, LightGBM | Pipeline 模式防泄漏，GridSearchCV 成熟 |
| **Gensim** | LDA 主题建模 | scikit-learn LDA | 更好的 LDA 实现，Phrases 检测 Bigram |
| **networkx** | 语义网络 | igraph | API 友好，中心性算法完整，社区检测内置 |

**不选择 transformers/BERT 的原因**:
- 需要 GPU（作品集不便携带）
- 模型文件大（>500MB），不适合 GitHub
- 推理速度慢（实时预测 API 无法秒回）

## Frontend: Vue3 + Vite + TypeScript

| 对比项 | Vue3 | React | Angular |
|--------|------|-------|---------|
| 学习曲线 | 低 | 中 | 高 |
| TypeScript | ✅ 原生 | ✅ | ✅ 原生 |
| UI 框架 | Element Plus | Ant Design | Material |
| 构建工具 | Vite | Vite/Next.js | Webpack |
| 中文社区 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |

**选择理由**:
- Element Plus 是成熟的中文 UI 框架
- Vite 开发体验极好（HMR <1s）
- Pinia 比 Vuex 更简洁（Composition API）
- ECharts 与 Vue 集成成熟

## Infra: Docker + GitHub Actions

**Docker**: 前后端分离部署，环境一致性
**GitHub Actions**: 免费 CI/CD，与 GitHub 仓库无缝集成
