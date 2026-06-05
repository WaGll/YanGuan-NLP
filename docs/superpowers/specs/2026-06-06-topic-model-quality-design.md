# 主题模型质量优化 — 设计文档

> 日期: 2026-06-06 | 状态: 待审批 | 项目: YanGuan-NLP

## 背景与问题

当前主题模型（BERTopic + LDA）在 B 站考研评论数据集上存在以下质量问题：

1. **Coherence 缺失**：BERTopic 的 coherence_score 直接设为 None，无有效评估指标
2. **关键词噪声**：口语化词汇（姐姐、大佬）、网络用语（ydys）、低信息量感性词（好听、可爱）混入主题关键词
3. **主题混杂**：同一主题包含不同语义维度的内容（如"数据相关"混入工具、资源、人物称谓）
4. **短文本稀疏**：单条评论 10-50 字，语义信息不足，主题-词分布不稳定

## 技术决策总结

| 决策 | 选择 | 理由 |
|------|------|------|
| 分词器 | pkuseg (web模型) 替代 jieba | 对网络非正式文本准确率更高，自带词性标注 |
| 噪声处理 | 词性过滤 + 停用词扩充 | 系统性 + 针对性双重保障 |
| 短文本 | 视频+时间窗口聚合 | 利用现有 video_id + create_time，实现简单效果好 |
| Coherence | NPMI + diversity + c_v 双轨 | 覆盖 BERTopic 内置指标和传统评估 |
| 主题命名 | 规则引擎 + LLM (qwen3:4b) 混合 | 规则兜底保证稳定性，LLM 增强可解释性 |
| LLM | Ollama qwen3:4b (本地) | 数据不出域，成本为零 |

## 架构变更总览

```
                          原流程
Raw CSV → Cleaner(jieba) → DB → TopicService(LDA/BERTopic) → API
                                     ↓
                              LabelGenerator(规则) → Topic.label

                          新流程
Raw CSV → Cleaner(pkuseg+POS过滤) → DB
                ↓                      ↓
         停用词扩充 + 同义词     AggregationService(视频+时间窗口)
                                       ↓
                                  CommentGroup 表
                                       ↓
                          TopicService(LDA/BERTopic+GridSearch)
                                ↓              ↓
                     Coherence双轨评估    LabelGenerator(规则)
                                               ↓
                                    LLMLabeler(qwen3:4b)
                                               ↓
                                         Topic.label
```

---

## 模块 1：分词器重构（pkuseg 替代 jieba）

**目标**：pkuseg (web模型) 替代 jieba 作为主分词器，通过配置开关控制，利用 web 模型提升网络文本分词准确率，同时通过词性标注支持后续噪声过滤。

**新增文件**：`backend/app/utils/tokenizer.py`

```python
class ChineseTokenizer:
    """中文分词器，pkuseg 主 + jieba 兜底"""
    def __init__(self, backend: TokenizerBackend, pos_filter: bool = True):
        ...
    def tokenize(self, text: str) -> list[TokenInfo]:
        """返回 [(word, pos_tag, is_noise), ...]"""
        ...
    def tokenize_batch(self, texts: list[str]) -> list[list[str]]:
        """批量分词，兼容现有接口"""
        ...
```

**关键决策**：
- 通过 `spacy-pkuseg` 加载 pkuseg `web` 模型（已安装 spacy-pkuseg 0.0.32）
- jieba 作为 fallback（pkuseg 不可用时自动降级）
- 配置项 `tokenizer_backend`：`"pkuseg"` | `"jieba"`，默认 `"jieba"` 保持向后兼容
- pkuseg 自定义词典迁移现有 `自定义字典.txt`

**改动**：
- 新建 `backend/app/utils/tokenizer.py`
- 修改 `backend/app/utils/resources.py` — 加载 pkuseg 模型 + 词典
- 修改 `backend/app/services/cleaner.py` — tokenize() 切换后端
- 修改 `backend/app/config.py` — 新增 `tokenizer_backend` 配置项

---

## 模块 2：文本清洗与噪声过滤增强

**目标**：扩充口语填充词和停用词，引入词性过滤系统性减少噪声。

**增强后的清洗管道**：
1. URL/HTML/@mentions/emoji 去除（保持现有逻辑）
2. B站 bracket emoji 去除（保持现有逻辑，确认覆盖完整）
3. 口语填充词去除：FILLER_WORDS 从 ~30 → ~80 词
4. pkuseg 分词 + 词性标注
5. **词性过滤（新增）**：
   - 过滤：nr(人名), nrf(姓), nrg(名), e(叹词), o(拟声词), y(语气词), u(助词), x(非语素字), w(标点)
   - 保留：n, v, a, d, i(成语), j(简称), l(习语)
6. 停用词过滤：扩充 ~100 词，分类管理
7. 同义词替换：扩充网络用语映射
8. Bigram 检测（保持现有逻辑）

**停用词扩充分类**：
- B站弹幕文化：好家伙、绝绝子、狂喜、泪目、破防、绷不住、笑死、太真实了
- 低信息量感性词：好听、好看、可爱、厉害、牛逼、无敌、真的假的
- 模糊称谓：姐姐、小姐姐、大佬、xd、家人、兄弟们、同志们
- 无意义缩写：ydys、yyds、xswl、nsdd、srds、u1s1
- 无意义副词/连词：这方面、怎么说、就是说、实际上、基本上

**改动**：
- 修改 `backend/app/utils/chinese.py` — 扩充 FILLER_WORDS，新增 POS_FILTER_RULES
- 修改 `backend/app/services/cleaner.py` — tokenize() 集成词性过滤
- 修改 `backend/data/merged_stopwords.txt` — 扩充分类区块
- 修改 `backend/data/同义词.txt` — 扩充网络用语映射

---

## 模块 3：短文本聚合（Video + Time Window）

**目标**：通过 video_id + 时间窗口将同视频短评论聚合为伪文档，提升文本丰富度。

**新增模型 CommentGroup**：
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增主键 |
| video_id | String(64) | 来源视频 ID |
| time_window_start | DateTime | 时间窗口起始 |
| time_window_end | DateTime | 时间窗口结束 |
| comment_count | Integer | 组内评论数 |
| aggregated_content | Text | 合并后原始文本 |
| aggregated_tokens_json | Text | 合并后 token 列表 |
| unique_comment_ids | Text | JSON 数组，来源评论 ID |
| is_aggregated | Boolean | 标记为聚合文档（默认 True） |
| created_at / updated_at | DateTime | 审计字段 |

**聚合逻辑**：
```python
class AggregationService:
    async def process(
        self,
        window_minutes: int = 60,
        min_comments: int = 3
    ) -> int:
        """按 (video_id, time_window) GROUP BY 聚合评论"""
```

**TopicService 适配**：
- `run_bertopic()` / `run_lda()` 新增参数 `source: str = "comment_group"`
- `source="comment_group"` 时从 CommentGroup 读取
- `source="comment"` 时从 Comment 读取（回退模式）

**配置项**：
- `aggregation_window_minutes: int = 60`
- `aggregation_min_comments: int = 3`
- `aggregation_enabled: bool = True`

**改动**：
- 新建 `backend/app/models/comment_group.py`
- 新建 `backend/app/services/aggregation.py`
- 修改 `backend/app/models/__init__.py`
- 修改 `backend/app/services/topic.py`
- 修改 `backend/app/config.py`

---

## 模块 4：Coherence 双轨评估 + BERTopic 参数调优

**目标**：为 BERTopic 补全完整多维度评估体系，引入参数自动搜索。

**评估指标**：

| 指标 | 计算方式 | 存储字段 |
|------|---------|---------|
| c_v coherence | 按 topic 拆分文档 → Gensim CoherenceModel | `Topic.coherence_score` |
| NPMI | BERTopic 内置，基于滑动窗口归一化点互信息 | `Topic.silhouette_score` (复用) |
| topic_diversity | top-10 关键词去重比例 | 新增 metric |
| topic_dominance | 最大主题文档占比 | 用于参数搜索惩罚项 |
| JS divergence | 主题间分布差异（已有） | 保留 |

**BERTopic 参数 Grid Search**：
```python
GRID = {
    "nr_topics": [8, 10, 12, 15, 18, "auto"],
    "n_neighbors": [10, 15, 20],
    "n_components": [5, 10],
    "min_cluster_size": [15, 25, 35],
}
SCORE = 0.4 * NPMI + 0.3 * diversity - 0.3 * max_topic_dominance_ratio
```

**改动**：
- 修改 `backend/app/services/topic.py`：
  - 新增 `_bertopic_grid_search()`
  - 新增 `_compute_bertopic_cv_coherence()`
  - 新增 `_compute_topic_diversity()`
  - 新增 `_compute_npmi()`

---

## 模块 5：规则 + LLM 混合主题命名

**目标**：规则引擎生成候选标签，LLM 精炼去歧义，提升主题可解释性。

**管道**：
```
top-15 关键词 + 3 条代表性评论
    ↓
LabelGenerator (规则引擎，增强至 20 domain)
    ↓ 候选标签 + 置信度
LLMLabeler (Ollama qwen3:4b)
    ↓  超时 10s → fallback 规则标签
最终标签 + needs_review 标记
```

**LLM Prompt 模板**：
```
你是考研领域的内容分析专家。以下是一个主题聚类结果：

关键词: {keywords}
代表性评论:
1. {comment_1}
2. {comment_2}
3. {comment_3}

候选标签: {rule_label}

请基于关键词和代表性评论，生成一个简洁的中文主题名（4-8字）。
要求：准确反映主题核心语义，使用考研领域常用表述。
如果候选标签已经合理，直接返回；否则生成更好的标签。

只返回主题名，不要额外解释。
```

**数据字段扩展**：
- `Topic.business_label_llm` — LLM 精炼标签
- `Topic.business_label_confidence` — 置信度
- `Topic.needs_review` — 低置信度人工审核标记

**改动**：
- 新建 `backend/app/services/llm_labeler.py`
- 修改 `backend/app/services/label_generator.py` — domain 14→20，优化匹配算法
- 修改 `backend/app/services/topic.py` — 命名管道编排
- 修改 `backend/app/models/topic.py` — 新增字段
- 修改 `backend/app/config.py` — Ollama 配置

---

## 数据迁移

所有改动涉及数据重新处理：
1. 清空 `comments` 表中清洗字段
2. 清空 `topics`、`topic_keywords`、`doc_topics`、`comment_groups` 表
3. 重新运行：`CleanerService.process_all()` → `AggregationService.process()` → `TopicService.run_bertopic()`
4. 运行脚本：`python scripts/run_pipeline.py --progress`

## 测试策略

| 层级 | 测试内容 |
|------|---------|
| 单元测试 | ChineseTokenizer 分词准确性、POS 过滤规则、停用词加载、Aggregation 逻辑 |
| 集成测试 | Cleaner 全管道（含 pkuseg）、BERTopic Grid Search、LLM Labeler |
| 质量测试 | Coherence 得分 > 0.3、topic_diversity > 0.6、主题间 JS divergence > 0.5 |
| 回归测试 | LDA 路径不受影响、API 响应格式兼容、jieba 回退正常 |

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| pkuseg 分词速度慢 | 数据量仅 2762 条，单次处理可接受；支持 jieba 回退 |
| qwen3:4b 推理质量不稳定 | 超时 + fallback 规则标签；温度设 0.3 减少随机性 |
| 聚合后文本过长 | 设置 token 上限（500），超出截断 |
| Grid Search 耗时 | 缓存中间结果；random_state 固定保证可复现 |
