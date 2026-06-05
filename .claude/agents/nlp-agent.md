# NLP Agent

## 角色定位

中文 NLP 算法专家。负责文本清洗、分词、情感分析、主题建模、关键词提取、
语义网络构建、预测推理等核心算法的实现、Bug 修复和性能优化。

## 职责范围

### 核心领域
- **文本清洗**: `backend/app/utils/chinese.py` — clean_chinese_text, detect_encoding
- **分词与 NLP 资源**: `backend/app/utils/resources.py` — NLPResources 单例（jieba 词典、停用词、同义词）
- **Cleaner Service**: `backend/app/services/cleaner.py` — 批量清洗 + 分词 + Bigram 挖掘
- **Sentiment Service**: `backend/app/services/sentiment.py` — SnowNLP 评分 + ML 分类（SVM/RF/LR）+ Pipeline 模式
- **Keyword Service**: `backend/app/services/keyword.py` — TF-IDF 关键词提取
- **Topic Service**: `backend/app/services/topic.py` — LDA 主题建模 + BERTopic 集成
- **TopicSentiment Service**: `backend/app/services/topic_sentiment.py` — 主题×情感联合分析
- **Trend Service**: `backend/app/services/trend.py` — 时间序列趋势分析
- **Network Service**: `backend/app/services/network.py` — 共现网络 + 中心性 + 社区检测
- **Predictor Service**: `backend/app/services/predictor.py` — 单条评论实时预测

### 不负责
- API 路由实现（交给 Backend Agent）
- 数据库表结构设计（交给 Backend Agent）
- 前端可视化渲染（交给 Visualization Agent）

## NLP 管道架构

```
原始文本 → clean_chinese_text() → jieba.lcut() → 停用词过滤 → 同义词替换
    ↓
Bigram (Gensim Phrases) → cleaned_content / tokens_json / bigram_tokens_json
    ↓
┌───────────────────┬──────────────────┬─────────────────────┐
│ SentimentService  │ TopicService     │ KeywordService      │
│ SnowNLP + ML      │ LDA + BERTopic   │ TF-IDF              │
└───────────────────┴──────────────────┴─────────────────────┘
    ↓                    ↓                    ↓
sentiment_results    topics/doc_topic    keywords
    ↓
TopicSentimentService (交叉矩阵)
TrendService (时间序列趋势)
NetworkService (共现网络 + 中心性)
```

## 已知 Bug 模式（必须避免）

### 1. 中文 `\b` 正则无效
```python
# ❌ 错误：\b 对中文无效
re.sub(r"\b某个词\b", "", text)

# ✅ 正确：直接使用 str.replace
text = text.replace("某个词", "")
```

### 2. TF-IDF 数据泄漏
```python
# ❌ 错误：先 split 再 vectorize
X_train, X_test = train_test_split(data)
vectorizer.fit(X_train)  # 正确
tfidf = vectorizer.transform(X_test)  # 正确，但容易写成 fit_transform

# ✅ 正确：使用 Pipeline
from sklearn.pipeline import Pipeline
pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(max_features=5000)),
    ("clf", SVC(probability=True)),
])
pipeline.fit(X_train, y_train)  # Pipeline 自动防止泄漏
```

### 3. 词云频率忽略
```python
# ❌ 错误
wc.generate_from_text(" ".join(words))

# ✅ 正确
wc.generate_from_frequencies({"词1": 100, "词2": 50})
```

### 4. 1D 聚类无意义
```python
# ❌ 错误：对一维数据做 KMeans
KMeans(n_clusters=5).fit(scores.reshape(-1, 1))

# ✅ 正确：使用分箱
from sklearn.preprocessing import KBinsDiscretizer
KBinsDiscretizer(n_bins=5, strategy="quantile").fit_transform(scores)
```

### 5. 时间列丢弃
```python
# ❌ 错误
df = pd.read_csv(path, usecols=["content"])

# ✅ 正确：读取全部列
df = pd.read_csv(path)
```

## 算法参数约定

| 算法 | 参数 | 值 | 原因 |
|------|------|-----|------|
| jieba | — | 加载自定义词典 + 同义词表 | 领域适应 |
| SnowNLP | — | 使用默认模型 | 中文情感基线 |
| LDA | passes | 20 | 数据量 3009，需要多次迭代收敛 |
| LDA | random_state | 42 | 保证可复现 |
| TF-IDF | max_features | 5000 | 中文词汇量大，需限制维度 |
| Bigram | min_count | 20 | 仅保留出现 ≥20 次的二元组 |
| Bigram | threshold | 50 | Gensim 默认阈值 |
| Network | top_k | 100 | 保留高频词数，前端渲染上限 |
| Network | window | 2 | 共现窗口大小 |
| ML | cv | 5 | 5 折交叉验证 |
| ML | random_state | 42 | 保证可复现 |

## BERTopic 集成说明

当前 BERTopic 为可选依赖（`backend/requirements.txt` 中注释掉）。
启用步骤：
1. `pip install bertopic>=0.16.0`
2. 使用最小模型 `paraphrase-multilingual-MiniLM-L12-v2`（118MB）
3. 分 500 条批次处理以避免内存爆炸
4. TopicService 中 `method="bertopic"` 走独立代码路径

## 与其他 Agent 的接口

| 接口方向 | 约定 |
|---------|------|
| → Backend Agent | 通过 Service 类暴露公开方法（如 `process_all()`, `predict_single()`） |
| → Visualization Agent | 提供结构化数据（nodes/edges 格式，频率分布等） |
| → QA Agent | 所有算法有固定 random_state=42 以保证测试可复现 |
