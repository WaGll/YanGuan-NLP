# 数据库设计决策

## 概述

11 个表的 SQLite 数据库，使用 SQLAlchemy async ORM 管理。

## 完整 Schema

### 1. comments — 评论主表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, autoincrement | 自增主键 |
| comment_id | VARCHAR(64) | UNIQUE, NOT NULL, INDEX | 原始评论 ID |
| parent_comment_id | VARCHAR(64) | NULL | 父评论 ID |
| create_time | BIGINT | NOT NULL | Unix 时间戳 |
| create_datetime | DATETIME | NULL | 解析后的 datetime |
| video_id | VARCHAR(64) | NULL, INDEX | 视频 ID |
| content | TEXT | NULL | 原始评论文本 |
| user_id | VARCHAR(64) | NULL | 用户 ID |
| nickname | VARCHAR(255) | NULL | 用户昵称 |
| avatar | TEXT | NULL | 头像 URL |
| sub_comment_count | INTEGER | NULL | 子评论数 |
| last_modify_ts | BIGINT | NULL | 最后修改时间戳 |
| cleaned_content | TEXT | NULL | 清洗后文本 |
| tokens_json | TEXT | NULL | 分词 JSON 列表 |
| bigram_tokens_json | TEXT | NULL | Bigram 分词 JSON |
| token_count | INTEGER | NULL | 有效 token 数 |
| created_at | DATETIME | NOT NULL | 记录创建时间 |
| updated_at | DATETIME | NOT NULL | 记录更新时间 |

### 2. keywords — 关键词表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK | 主键 |
| word | VARCHAR(128) | UNIQUE, NOT NULL, INDEX | 关键词 |
| frequency | INTEGER | NOT NULL | 词频 |
| tfidf_score | FLOAT | NULL | TF-IDF 得分 |

### 3. topics — 主题表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK | 主键 |
| method | VARCHAR(32) | NOT NULL | 算法: lda / bertopic |
| topic_index | INTEGER | NOT NULL | 主题序号 |
| label | VARCHAR(255) | NULL | 主题标签 |
| coherence_score | FLOAT | NULL | 一致性得分 |
| created_at / updated_at | DATETIME | — | 时间戳 |

### 4. topic_keywords — 主题关键词表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK | 主键 |
| topic_id | INTEGER | FK → topics.id | 主题外键 |
| word | VARCHAR(128) | NOT NULL | 关键词 |
| weight | FLOAT | NOT NULL | 权重 |
| rank | INTEGER | NOT NULL | 排名 |

### 5. doc_topic — 文档-主题分配表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK | 主键 |
| comment_id | INTEGER | FK → comments.id | 评论外键 |
| topic_id | INTEGER | FK → topics.id | 主题外键 |
| probability | FLOAT | NOT NULL | 分配概率 |
| is_primary | BOOLEAN | DEFAULT FALSE | 是否主导主题 |

### 6. sentiment_results — 情感结果表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK | 主键 |
| comment_id | INTEGER | FK → comments.id, UNIQUE | 评论外键（一对一） |
| snownlp_score | FLOAT | NOT NULL | SnowNLP 0~1 得分 |
| sentiment_class | VARCHAR(16) | NOT NULL | positive/negative/neutral |
| ml_predicted | VARCHAR(16) | NULL | ML 模型预测 |
| ml_confidence | FLOAT | NULL | ML 置信度 |

### 7. sentiment_ml_scores — ML 评估表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK | 主键 |
| model_name | VARCHAR(64) | NOT NULL | SVM / RF / LR |
| cv_mean | FLOAT | NOT NULL | 交叉验证均值 |
| cv_std | FLOAT | NOT NULL | 交叉验证标准差 |
| best_params_json | TEXT | NULL | 最优参数 JSON |

### 8. network_nodes — 网络节点表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK | 主键 |
| word | VARCHAR(128) | UNIQUE, NOT NULL, INDEX | 节点词 |
| frequency | INTEGER | NOT NULL | 词频 |
| degree_centrality | FLOAT | NOT NULL | 度中心性 |
| betweenness_centrality | FLOAT | NOT NULL | 介数中心性 |
| eigenvector_centrality | FLOAT | NOT NULL | 特征向量中心性 |
| community_id | INTEGER | NOT NULL | 社区 ID |

### 9. network_edges — 网络边表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK | 主键 |
| source_word | VARCHAR(128) | FK → network_nodes.word | 源节点 |
| target_word | VARCHAR(128) | FK → network_nodes.word | 目标节点 |
| weight | INTEGER | NOT NULL | 共现权重 |

### 10. trend_series — 趋势数据表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK | 主键 |
| series_type | VARCHAR(32) | NOT NULL | 类型: sentiment / keyword / topic |
| series_key | VARCHAR(128) | NOT NULL | 系列标识 |
| granularity | VARCHAR(16) | NOT NULL | 聚合粒度: day / week / month |
| bucket_start | DATETIME | NOT NULL | 时间桶起始 |
| avg_sentiment | FLOAT | NULL | 平均情感分 |
| comment_count | INTEGER | NOT NULL | 评论数 |

### 11. pipeline_runs — 管道运行记录表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK | 主键 |
| status | VARCHAR(32) | NOT NULL | 状态: pending/running/completed/failed |
| stage | VARCHAR(64) | NOT NULL | 当前阶段 |
| started_at | DATETIME | NULL | 开始时间 |
| completed_at | DATETIME | NULL | 完成时间 |
| error_message | TEXT | NULL | 错误信息 |
| created_at / updated_at | DATETIME | — | 时间戳 |

## 设计原则

### 1. 外键关系（ON DELETE CASCADE 不使用）
- SQLite 默认不强制外键（需 `PRAGMA foreign_keys=ON`）
- 删除采用应用层级联（先删子表再删主表）
- 原因: 更好的可控性和错误处理

### 2. JSON 字符串存储
- `tokens_json`、`bigram_tokens_json` 使用 TEXT 存储
- 原因: SQLite 的 JSON 支持有限，应用层解析更灵活
- 读取后 `json.loads()` 即可

### 3. 唯一约束
- `comment_id`: 防止重复导入
- `sentiment_results.comment_id`: 一对一关系
- `network_nodes.word`: 节点唯一

### 4. 索引策略
- 主键自动索引
- 外键手动加索引（`comment_id`, `video_id`）
- 高频查询字段加索引（`word`, `create_time`）

### 5. 时间戳混入 (TimestampMixin)
- 所有表继承 `TimestampMixin`
- 提供 `created_at` 和 `updated_at`
- `server_default=func.now()` 确保数据库端默认值

## ER 关系图

```
comments ──1:1── sentiment_results
comments ──1:N── doc_topic
topics   ──1:N── topic_keywords
topics   ──1:N── doc_topic
network_nodes ──1:N── network_edges (source)
network_nodes ──1:N── network_edges (target)

独立表: keywords, sentiment_ml_scores, trend_series, pipeline_runs
```
