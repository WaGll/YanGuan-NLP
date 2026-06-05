# 已知 Bug 模式与修复

本文档记录项目中已发现的关键 Bug 及其修复模式。每次遇到同类问题，**必须**参考此文档。

---

## Bug #1: 中文 `\b` 正则边界无效

**位置**: 原 `data_cleaner.py:50`
**严重度**: 高
**发现日期**: 2026-06-01

### 问题
Python 正则的 `\b` (word boundary) 对中文字符无效。因为 `\b` 依赖 `\w`（字母数字下划线），
而中文字符不属于 `\w` 类别。

```python
# ❌ 错误
text = re.sub(r"\b啊啊\b", "", text)  # 对中文无效

# ✅ 正确
text = text.replace("啊啊", "")  # 直接字符串替换
```

### 修复
在 `backend/app/utils/chinese.py` 的 `clean_chinese_text()` 中：
- 使用 `str.replace()` 逐一替换 FILLER_WORDS
- 对于复杂模式使用明确的中文字符范围 `[一-鿿]`

### 教训
处理中文文本时，**永远不要使用 `\b`**。使用以下替代方案：
- 简单替换: `str.replace()`
- 模式匹配: `re.sub(r"[一-鿿]+pattern", ...)`
- 分词后过滤: 先 jieba 分词，再过滤 token

---

## Bug #2: TF-IDF 数据泄漏

**位置**: 原 `sentiment_analyzer.py:34`
**严重度**: 高
**发现日期**: 2026-06-01

### 问题
在 train_test_split 之前对整个数据集做 TF-IDF fit_transform，导致测试集的信息泄漏到训练集。

```python
# ❌ 错误
X = vectorizer.fit_transform(all_texts)  # 在所有数据上 fit
X_train, X_test, y_train, y_test = train_test_split(X, y)
# 测试集参与了 vectorizer 的 fit → 数据泄漏！

# ✅ 正确: 使用 Pipeline + GridSearchCV
from sklearn.pipeline import Pipeline
pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(max_features=5000)),
    ("clf", SVC(probability=True, random_state=42)),
])
grid = GridSearchCV(pipeline, param_grid, cv=5)  # Pipeline 自动防止泄漏
```

### 修复
在 `backend/app/services/sentiment.py` 中：
1. 定义 Pipeline（TF-IDF + classifier）
2. 使用 GridSearchCV 做交叉验证
3. 不在 Pipeline 外部单独 fit vectorizer

### 教训
任何涉及 fit/transform 的预处理步骤，必须包装在 Pipeline 中。
GridSearchCV 的 `cv` 参数会在每个 fold 内对训练集 fit，测试集仅 transform。

---

## Bug #3: WordCloud 忽略频率

**位置**: 原 `text_analyzer.py:25`
**严重度**: 中
**发现日期**: 2026-06-01

### 问题
`WordCloud.generate_from_text()` 内部重新分词和计数，可能产生与已有词频分析不一致的结果。

```python
# ❌ 错误
wc = WordCloud(font_path="SimHei.ttf")
wc.generate_from_text(" ".join(words))  # 内部重新分词 → 词频不一致

# ✅ 正确
wc = WordCloud(font_path="SimHei.ttf")
wc.generate_from_frequencies({"词1": 100, "词2": 50})  # 使用已计算的词频
```

### 修复
- 后端提供词频字典 API
- 前端使用 `wordcloud2.js` 渲染（通过频率数组）

### 教训
可视化组件应使用**已分析的数据**，不要重新计算统计信息。

---

## Bug #4: 1D 聚类无意义

**位置**: 原 `cluster_classifier.py:24`
**严重度**: 中
**发现日期**: 2026-06-01

### 问题
对一维数据（如情感分数 0-1）使用 KMeans 聚类，产生无意义的聚类结果。

```python
# ❌ 错误
scores = [0.2, 0.3, 0.5, 0.6, 0.8, 0.9]
KMeans(n_clusters=3).fit(np.array(scores).reshape(-1, 1))
# 聚类结果只反映值的排序，无实际意义

# ✅ 正确
from sklearn.preprocessing import KBinsDiscretizer
kbins = KBinsDiscretizer(n_bins=3, strategy="quantile")
kbins.fit_transform(np.array(scores).reshape(-1, 1))
# 基于分位数的分箱更有意义
```

### 修复
使用 `KBinsDiscretizer` 替代 KMeans，或直接使用阈值分类（SnowNLP >0.6 positive, <0.4 negative）。

### 教训
聚类需要多维特征才有意义。一维数据应使用分箱或阈值分类。

---

## Bug #5: CSV 时间列丢弃

**位置**: 原 `data_cleaner.py:74`
**严重度**: 中
**发现日期**: 2026-06-01

### 问题
使用 `usecols=["content"]` 读取 CSV，丢弃了 `create_time` 等关键列，
导致趋势分析无法进行。

```python
# ❌ 错误
df = pd.read_csv(path, usecols=["content"])  # 只保留 content 列

# ✅ 正确
df = pd.read_csv(path)  # 读取全部列
```

### 修复
在 `backend/app/services/data_loader.py` 中：
- 读取 CSV 全部 11 列
- 在 Comment 模型中定义所有字段（见 `models/comment.py`）
- 原始数据全部入库，按需查询

### 教训
数据导入阶段要保留全部原始信息。不要在 ETL 中丢弃数据，
在查询/分析时按需选择。

---

## Bug #6: temp.csv 竞态条件

**位置**: 原 `data_cleaner.py:71`
**严重度**: 低
**发现日期**: 2026-06-01

### 问题
多次运行时 temp.csv 可能被覆盖，导致数据处理不一致。

### 修复
使用 chardet 检测编码后直接读取原文件，不产生中间文件：
```python
encoding = detect_encoding(file_path)
df = pd.read_csv(file_path, encoding=encoding)
```

### 教训
避免在数据处理管道中产生临时文件。如果必须产生，使用唯一的临时文件名（`tempfile` 模块）。

---

## Bug #7: `min`/`max` 变量名覆盖内置函数

**位置**: 原 `lda_modeler.py:39`
**严重度**: 低
**发现日期**: 2026-06-01

### 问题
```python
# ❌ 错误
min = 2  # 覆盖了 Python 内置 min()
max = 10  # 覆盖了 Python 内置 max()

# ✅ 正确
min_k = 2
max_k = 10
```

### 修复
重命名为 `min_k`/`max_k` 或 `n_topics_min`/`n_topics_max`。

### 教训
永远不要使用 Python 内置函数名作为变量名。常见冲突名：
`min`, `max`, `list`, `dict`, `set`, `str`, `id`, `type`, `input`, `sum`, `all`, `any`

---

## 防范清单

在编写或审查代码时，检查以下模式：

1. 🔍 正则中有 `\b` 吗？→ 中文场景用 `str.replace()`
2. 🔍 TF-IDF 在 split 之前 fit 了吗？→ 必须用 Pipeline
3. 🔍 WordCloud 用了 `generate_from_text()` 吗？→ 改用 `generate_from_frequencies()`
4. 🔍 对一维数据做了 KMeans 吗？→ 改用 KBinsDiscretizer 或阈值
5. 🔍 `pd.read_csv()` 有 `usecols` 参数吗？→ 检查是否丢列
6. 🔍 变量名是 Python 内置函数吗？→ 重命名
7. 🔍 产生了中间临时文件吗？→ 用流式处理或直接操作原文件
