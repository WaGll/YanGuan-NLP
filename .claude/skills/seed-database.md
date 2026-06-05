# Skill: seed-database

## 描述

导入 CSV 数据到 SQLite 数据库，并运行完整的 NLP 分析流水线。
适用于首次项目初始化或数据更新后重新导入。

## 触发条件

- 用户说"导入数据"、"seed 数据库"、"初始化数据库"
- 项目首次克隆后
- CSV 数据更新后

## 执行步骤

### 步骤 1: 验证前置条件

```bash
# 确认 CSV 数据文件存在
ls -la backend/data/毕业去向讨论.csv
ls -la backend/data/merged_stopwords.txt
ls -la backend/data/自定义字典.txt
ls -la backend/data/同义词.txt

# 确认 Python 依赖已安装
cd backend && python -c "import jieba, snownlp, sklearn, gensim, networkx; print('OK')"
```

如果依赖缺失：
```bash
cd backend && pip install -r requirements.txt
```

### 步骤 2: 启动后端服务（如未启动）

```bash
cd backend && uvicorn app.main:app --reload &
```

确认服务健康：
```bash
curl http://localhost:3001/api/health
```

### 步骤 3: 运行 seed 脚本

```bash
cd backend && python scripts/seed_db.py
```

脚本执行内容：
1. 创建所有数据库表（如已存在则跳过）
2. 读取 CSV 并导入到 `comments` 表（INSERT OR IGNORE 去重）
3. 运行 CleanerService → 清洗 + 分词 + Bigram
4. 运行 SentimentService → SnowNLP + ML 分类
5. 运行 KeywordService → TF-IDF 关键词
6. 运行 TopicService → LDA 主题建模
7. 运行 NetworkService → 共现网络 + 中心性
8. 运行 TrendService → 时间趋势聚合
9. 记录 PipelineRun 状态

### 步骤 4: 验证结果

```bash
# 检查数据量
curl -s http://localhost:3001/api/dashboard | python -m json.tool

# 预期输出:
# {
#   "code": 200,
#   "data": {
#     "total_comments": 3009,
#     ...
#   }
# }
```

### 步骤 5: 处理错误

| 错误 | 解决方案 |
|------|---------|
| `ModuleNotFoundError: No module named 'xxx'` | `pip install xxx` |
| `NLPResources 尚未加载` | 检查 data_dir 路径，确保 stopwords 文件存在 |
| `数据库锁` | SQLite WAL 模式自动处理，重试即可 |
| `CSV 编码错误` | chardet 自动检测编码，如失败则手动指定 `encoding="gbk"` |

## 输出

- SQLite 数据库文件 `backend/yanguan.db`
- 控制台日志显示每步处理进度
- PipelineRun 记录在数据库中

## 预计耗时

- 3009 条数据全管道处理: ~3-5 分钟
- 其中 LDA 主题建模最耗时 (~2 分钟)
