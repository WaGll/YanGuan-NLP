# 架构决策记录 (ADR)

## ADR-001: 选择 SQLite 而非 MySQL/PostgreSQL

**日期**: 2026-06-01
**状态**: 已采纳
**决策者**: 项目组

### 背景
项目需要持久化存储，需要在 SQLite、MySQL、PostgreSQL 之间选择。

### 决策
选择 **SQLite + aiosqlite**。

### 理由
1. **作品集项目**: 单机部署即可，无需独立数据库服务器
2. **零配置**: 不需要安装 MySQL Server，降低使用者门槛
3. **数据量小**: 3009 条评论，SQLite 完全胜任
4. **可迁移**: SQLAlchemy ORM 使得未来迁移到 PostgreSQL 只需改一行连接字符串
5. **WAL 模式**: 开启 WAL 后支持并发读写，性能足够

### 后果
- ✅ 部署极简，一个文件即数据库
- ✅ Docker 单容器即可运行
- ⚠️ 并发写入受限（WAL 已缓解）
- ⚠️ 不支持某些高级 SQL 特性（窗口函数等可用但不推荐）

---

## ADR-002: async/await 全链路

**日期**: 2026-06-01
**状态**: 已采纳

### 背景
FastAPI 支持 async，SQLAlchemy 2.0 支持 async。选择同步还是异步？

### 决策
所有端点和 Service 层使用 **async/await**。

### 理由
1. FastAPI 原生 async 性能更好
2. aiosqlite 是异步驱动，不阻塞事件循环
3. I/O 密集型 NLP 管道可以并发处理
4. 统一风格降低认知负担

### 后果
- ✅ 一致的 async 调用链
- ✅ 更好的并发性能
- ⚠️ 同步库（jieba, SnowNLP）需在线程池中运行
- ⚠️ 调试复杂度略高

---

## ADR-003: SQLite WAL 模式

**日期**: 2026-06-01
**状态**: 已采纳

### 决策
数据库连接时始终启用 WAL (Write-Ahead Logging) 模式。

### 实现
```python
@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()
```

### 理由
1. WAL 允许并发读和写（默认 DELETE 模式读写互斥）
2. API 请求（读）和管道处理（写）可同时进行
3. SQLite 3.7+ 默认支持，无需额外配置

---

## ADR-004: sklearn Pipeline 防数据泄漏

**日期**: 2026-06-01
**状态**: 已采纳

### 背景
原代码中 TF-IDF vectorizer 在 split 之前 fit，导致训练集信息泄漏到测试集。

### 决策
使用 `sklearn.pipeline.Pipeline` 包裹 vectorizer 和 classifier。

### 实现
```python
pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(max_features=5000)),
    ("clf", SVC(probability=True, random_state=42)),
])
grid = GridSearchCV(pipeline, param_grid, cv=5)
```

### 后果
- ✅ 交叉验证中 vectorizer 仅对训练 fold 做 fit
- ✅ 代码更简洁，一个 pipeline 对象替代多个步骤
- ✅ 与 GridSearchCV 完美配合

---

## ADR-005: NLPResources 单例模式

**日期**: 2026-06-01
**状态**: 已采纳

### 背景
jieba 词典、停用词、同义词表需要在应用启动时加载一次，所有 request 共享。

### 决策
使用 **单例模式**（Singleton）管理 NLP 资源。

### 实现
```python
class NLPResources:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
```

### 理由
1. 避免每个请求重复加载 stopwords（1642 条）和 synonym（74 条）
2. jieba 词典只需加载一次
3. 线程安全（FastAPI async 单线程事件循环）

---

## ADR-006: Vue3 + Element Plus 按需引入

**日期**: 2026-06-02
**状态**: 已采纳

### 背景
Element Plus 完整包体积大（~1MB gzipped），需要优化。

### 决策
使用 `unplugin-vue-components` + `unplugin-auto-import` 实现按需引入。

### 实现
```typescript
// vite.config.ts
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

Components({ resolvers: [ElementPlusResolver()] })
```

### 后果
- ✅ 仅打包实际使用的组件 → <500KB gzipped
- ✅ 无需手动 import 组件和样式
- ⚠️ 构建时依赖插件正确解析

---

## ADR-007: 前后端分离 + Nginx 反向代理

**日期**: 2026-06-02
**状态**: 已采纳

### 决策
- 开发环境：Vite proxy (`/api` → `localhost:8000`)
- 生产环境：Nginx 反向代理 (`/api/` → `backend:8000`)

### 实现
开发 (`vite.config.ts`):
```typescript
server: { proxy: { '/api': { target: 'http://localhost:8000' } } }
```

生产 (`nginx.conf`):
```nginx
location /api/ { proxy_pass http://backend:8000; }
```

### 理由
1. 开发时前端独立运行（HMR 快）
2. 生产时单域名访问（无 CORS 问题）
3. Nginx 提供静态文件服务、gzip、缓存等

---

## ADR-008: 11 表数据模型（非范式化部分字段）

**日期**: 2026-06-02
**状态**: 已采纳

### 背景
Comment 表的 tokens_json 和 bigram_tokens_json 以 JSON 字符串存储。

### 决策
分析结果以 **JSON 字符串** 存储在 Comment 表中，而非完全范式化。

### 理由
1. tokens 列表长度可变（2-50），分离表效率低
2. JSON 适合快速读取和前端展示
3. SQLite 支持 JSON 函数（可未来升级为 JSON 列类型）

### 后果
- ✅ 读取性能好（一次查询获取所有字段）
- ⚠️ 无法在 SQL 层面对 token 做查询（通常不需要）
- ⚠️ JSON 字符串无 schema 验证（应用层保证）
