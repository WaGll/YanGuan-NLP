"""
主题建模服务

提供 LDA 主题建模（Gensim）、BERTopic 存根，以及主题-文档分配的持久化。
"""

import json
import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from gensim.corpora import Dictionary
from gensim.models import CoherenceModel, LdaModel, TfidfModel
from scipy.spatial.distance import jensenshannon
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.models.comment_group import CommentGroup
from app.models.topic import DocTopic, Topic, TopicKeyword
from app.services.label_generator import TopicLabelGenerator

logger = logging.getLogger(__name__)


class TopicService:
    """主题建模服务。

    基于评论分词数据，使用 Gensim LDA 进行主题建模，
    自动选择最佳主题数 k，持久化主题、关键词和文档分配。
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # 数据加载
    # ------------------------------------------------------------------

    async def _load_documents(
        self, source: str = "comment_group"
    ) -> tuple[list[int], list[list[str]], list[str]]:
        """加载用于主题建模的文档。

        Args:
            source: 数据来源 — "comment_group" 从聚合表读取，"comment" 从原始评论读取

        Returns:
            (doc_ids, texts, docs_joined) 三元组:
            - doc_ids: 文档ID列表
            - texts: 分词列表的列表（给 LDA）
            - docs_joined: 空格连接的分词字符串列表（给 BERTopic）
        """
        if source == "comment_group":
            return await self._load_from_comment_groups()
        else:
            return await self._load_from_comments()

    async def _load_from_comments(
        self,
    ) -> tuple[list[int], list[list[str]], list[str]]:
        """从原始评论表加载文档。"""
        result = await self.db.execute(
            select(Comment.id, Comment.tokens_json).where(
                Comment.tokens_json.isnot(None),
                Comment.token_count > 0,
            )
        )
        rows = result.all()
        return self._parse_rows(rows)

    async def _load_from_comment_groups(
        self,
    ) -> tuple[list[int], list[list[str]], list[str]]:
        """从评论聚合表加载文档。"""
        result = await self.db.execute(
            select(
                CommentGroup.id,
                CommentGroup.aggregated_tokens_json,
            ).where(
                CommentGroup.aggregated_tokens_json.isnot(None),
                CommentGroup.comment_count > 0,
            )
        )
        rows = result.all()

        if not rows:
            logger.warning("CommentGroup 表为空，回退到原始评论数据")
            return await self._load_from_comments()

        logger.info("从 CommentGroup 加载 %d 条聚合文档", len(rows))
        return self._parse_rows(rows)

    @staticmethod
    def _parse_rows(
        rows: list[Any],
    ) -> tuple[list[int], list[list[str]], list[str]]:
        """解析数据库行，提取 tokens。

        Args:
            rows: [(id, tokens_json), ...] 的查询结果

        Returns:
            (ids, texts, docs_joined)
        """
        doc_ids: list[int] = []
        texts: list[list[str]] = []
        docs_joined: list[str] = []

        for doc_id, tokens_json in rows:
            try:
                tokens = json.loads(tokens_json)
                if tokens and len(tokens) >= 2:
                    texts.append(tokens)
                    docs_joined.append(" ".join(tokens))
                    doc_ids.append(doc_id)
            except (json.JSONDecodeError, TypeError):
                continue

        return doc_ids, texts, docs_joined

    # ------------------------------------------------------------------
    # 公开方法
    # ------------------------------------------------------------------

    async def run_lda(
        self, min_k: int = 4, max_k: int = 15, source: str = "comment_group"
    ) -> int:
        """运行 LDA 主题建模，自动选择最佳 k。

        步骤:
        1. 加载所有评论的 tokens_json（支持聚合/原始两种数据源）
        2. 构建 Gensim 词典和语料库
        3. 对 [min_k, max_k] 范围内的 k 训练 LDA，计算一致性分数
        4. 选择一致性最高的 k 作为最佳主题数
        5. 持久化主题、主题关键词、文档-主题分配

        Args:
            min_k: 最小主题数
            max_k: 最大主题数
            source: 数据来源 — "comment_group" | "comment"

        Returns:
            最佳 k 值
        """
        # 1. 加载分词数据
        comment_ids, texts, _ = await self._load_documents(source)

        if len(texts) < 10:
            logger.warning("有效文档数不足 %d 篇，无法运行 LDA", len(texts))
            return 0

        # 2. 构建词典和语料库
        dictionary = Dictionary(texts)
        # 过滤极端词频
        dictionary.filter_extremes(no_below=2, no_above=0.8)
        bow_corpus = [dictionary.doc2bow(text) for text in texts]

        # TF-IDF 加权：抑制跨文档高频词对主题建模的支配
        tfidf = TfidfModel(bow_corpus)
        corpus = tfidf[bow_corpus]

        # 3. 训练多个 k 的 LDA 模型，计算一致性
        best_k = min_k
        best_coherence = -1.0
        best_model = None
        best_corpus_topics = None

        for k in range(min_k, max_k + 1):
            try:
                lda = LdaModel(
                    corpus=corpus,
                    id2word=dictionary,
                    num_topics=k,
                    random_state=42,
                    passes=20,
                    alpha="auto",
                    eta="auto",
                )
                coherence_model = CoherenceModel(
                    model=lda,
                    texts=texts,
                    dictionary=dictionary,
                    coherence="c_v",
                )
                coherence = coherence_model.get_coherence()

                # 计算主题大小均衡性（抑制一主题独大的情况）
                corpus_topics = [
                    lda.get_document_topics(doc, minimum_probability=0.01)
                    for doc in corpus
                ]
                topic_counts = Counter()
                for doc_topics in corpus_topics:
                    if doc_topics:
                        dominant = max(doc_topics, key=lambda x: x[1])[0]
                        topic_counts[dominant] += 1
                total_docs = len(corpus)
                max_topic_ratio = max(topic_counts.values()) / total_docs if topic_counts else 1.0
                # 均衡性惩罚：某主题占比 >60% 时，按比例扣分
                balance_penalty = max(0.0, (max_topic_ratio - 0.6) * 2.0)
                adjusted_coherence = coherence - balance_penalty

                logger.info("k=%d, coherence=%.4f, max_topic_ratio=%.2f, adjusted=%.4f",
                             k, coherence, max_topic_ratio, adjusted_coherence)

                if adjusted_coherence > best_coherence:
                    best_coherence = adjusted_coherence
                    best_k = k
                    best_model = lda
                    # 获取每个文档的主题分布
                    best_corpus_topics = corpus_topics
            except Exception as e:
                logger.error("k=%d 训练失败: %s", k, e)
                continue

        if best_model is None:
            logger.warning("所有 k 的 LDA 模型训练均失败")
            return 0

        logger.info("最佳主题数 k=%d, coherence=%.4f", best_k, best_coherence)

        # 4. 计算每主题独立一致性分数
        per_topic_coherence = self._compute_per_topic_coherence(
            best_model, texts, dictionary
        )

        # 5. 清除旧的 LDA 数据
        await self._clear_old_lda_data()

        # 6. 持久化主题（先存规则标签，再批量 LLM 精炼）
        topic_map = {}  # topic_index -> Topic ORM 对象
        topic_data_for_llm: list[dict] = []  # 供批量 LLM 调用

        for topic_idx in range(best_k):
            # 基于 Top-3 关键词生成关键词拼接标签
            top_3 = best_model.show_topic(topic_idx, topn=3)
            label = " · ".join(w for w, _ in top_3)

            # 基于 Top-10 关键词生成业务主题标签
            top_10 = best_model.show_topic(topic_idx, topn=10)
            business_label = TopicLabelGenerator.generate(
                [(w, float(p), i + 1) for i, (w, p) in enumerate(top_10)]
            )

            # 获取 Top-15 关键词
            top_15 = best_model.show_topic(topic_idx, topn=15)
            keywords = [w for w, _ in top_15]

            # 获取该主题代表性评论
            lda_rep = []
            if best_corpus_topics:
                for doc_idx, doc_topics in enumerate(best_corpus_topics):
                    if doc_topics and max(doc_topics, key=lambda x: x[1])[0] == topic_idx:
                        lda_rep.append("".join(texts[doc_idx]))
                        if len(lda_rep) >= 3:
                            break

            # 领域建议（来自 TopicLabelGenerator 的 top-2 领域匹配）
            domain_hint = self._get_domain_hint(
                [(w, float(p), i + 1) for i, (w, p) in enumerate(top_10)]
            )

            coherence = per_topic_coherence.get(topic_idx, best_coherence)

            # 先用规则标签写入
            topic = Topic(
                method="lda",
                topic_index=topic_idx,
                label=label,
                business_label=business_label,
                coherence_score=coherence,
                business_label_llm=None,
                business_label_confidence=1.0,
                needs_review=False,
            )
            self.db.add(topic)
            await self.db.flush()  # 获取 id
            topic_map[topic_idx] = topic

            topic_data_for_llm.append({
                "topic_index": topic_idx,
                "keywords": keywords,
                "comments": lda_rep,
                "rule_label": business_label,
                "coherence_score": coherence,
                "domain_hint": domain_hint,
            })

        # 批量 LLM 精炼
        await self._apply_llm_batch_labels(topic_data_for_llm, topic_map)

        # 7. 持久化主题关键词（前 10 个）
        for topic_idx in range(best_k):
            top_words = best_model.show_topic(topic_idx, topn=10)
            for rank, (word, weight) in enumerate(top_words, start=1):
                self.db.add(
                    TopicKeyword(
                        topic_id=topic_map[topic_idx].id,
                        word=word,
                        weight=float(weight),
                        rank=rank,
                    )
                )

        # 8. 持久化文档-主题分配
        assert best_corpus_topics is not None
        for doc_idx, doc_topics in enumerate(best_corpus_topics):
            if not doc_topics:
                continue
            comment_id = comment_ids[doc_idx]
            # 找到主导主题
            dominant_topic_idx, dominant_prob = max(doc_topics, key=lambda x: x[1])
            for topic_idx, prob in doc_topics:
                self.db.add(
                    DocTopic(
                        comment_id=comment_id,
                        topic_id=topic_map[topic_idx].id,
                        probability=float(prob),
                        is_primary=(topic_idx == dominant_topic_idx),
                    )
                )

        # 9. 评估主题分离度
        separation = self.compute_topic_separation(best_model, best_k)
        logger.info("主题分离度: avg_overlap=%.3f, js_div=%s",
                     separation["average_overlap"] if separation else 0,
                     separation.get("js_divergence", []))

        # 10. 保存 LDA 模型和词典到磁盘（供预测服务使用）
        self._save_model(best_model, dictionary)

        await self.db.commit()
        logger.info("LDA 主题建模完成，k=%d，已持久化 %d 个主题", best_k, best_k)
        return best_k

    async def run_bertopic(
        self, source: str = "comment_group", grid_search: bool = False
    ) -> int:
        """运行 BERTopic 主题建模。

        使用本地 bge-small-zh-v1.5 Embedding 模型，
        以 TF-IDF 作为 fallback 策略（Embedding 不可用时）。
        BERTopic 自动发现主题数，c-TF-IDF 提取主题关键词。

        Args:
            source: 数据来源 — "comment_group" | "comment"

        Returns:
            发现的主题数量，失败时返回 0
        """
        import time as _time

        _t_start = _time.monotonic()

        try:
            from bertopic import BERTopic  # noqa: F811
        except ImportError:
            logger.error("BERTopic 未安装，请执行: pip install bertopic sentence-transformers")
            return 0

        # 1. 加载分词数据（空格分隔 → BERTopic CountVectorizer 直接 split）
        comment_ids, _, docs = await self._load_documents(source)

        if len(docs) < 10:
            logger.warning("BERTopic: 有效文档数不足 %d 篇，无法运行", len(docs))
            return 0

        logger.info("BERTopic: 加载 %d 条文档（source=%s）", len(docs), source)

        # 2. 加载 Embedding 模型 + 构建 CountVectorizer
        from app.config import settings
        from sklearn.feature_extraction.text import CountVectorizer

        # Embedding: 尝试本地 BGE 模型（语义表示）
        embedding_model = self._create_embedding_model(settings)
        if embedding_model is None:
            logger.warning("BERTopic: Embedding 模型不可用，跳过")
            return 0

        # CountVectorizer: 分词后空格连接 → tokenizer=str.split
        # 用于 c-TF-IDF 关键词提取
        # 参数自适应：文档数少时放宽过滤条件
        n_docs = len(docs)
        if n_docs < 200:
            # 少量文档：降低 max_df 过滤力度，确保 c-TF-IDF 有足够词汇
            vec_max_df = 1.0
            vec_min_df = 1
        else:
            vec_max_df = 0.7
            vec_min_df = 2
        vectorizer = CountVectorizer(
            tokenizer=lambda x: x.split(),
            lowercase=False,
            max_df=vec_max_df,
            min_df=vec_min_df,
            max_features=min(3000, n_docs * 20),  # 自适应特征上限
        )

        # 3. 训练 BERTopic 模型（可选 Grid Search）
        from hdbscan import HDBSCAN
        from umap import UMAP

        if grid_search:
            logger.info("BERTopic: 启动 Grid Search...")
            best_params = await self._bertopic_grid_search(docs)
        else:
            best_params = {"nr_topics": 12, "n_neighbors": 15, "n_components": 5,
                          "min_cluster_size": 25, "score": 0.0}

        # HDBSCAN 参数自适应：小数据集使用更小的 min_cluster_size
        if n_docs < 50:
            mcs = max(2, n_docs // 15)  # 极小数据集：每个主题约 15% 文档
            ms = 1
        elif n_docs < 100:
            mcs = max(3, n_docs // 12)
            ms = max(1, mcs // 3)
        elif n_docs < 500:
            mcs = max(5, n_docs // 20)
            ms = max(2, mcs // 3)
        else:
            mcs = best_params.get("min_cluster_size", 25)
            ms = max(5, mcs // 3)

        hdbscan_model = HDBSCAN(
            min_cluster_size=mcs,
            min_samples=ms,
            metric="euclidean",
            cluster_selection_method="eom",
            prediction_data=True,
        )
        logger.info("BERTopic: HDBSCAN min_cluster_size=%d, min_samples=%d (n_docs=%d)", mcs, ms, n_docs)

        umap_model = UMAP(
            n_neighbors=best_params.get("n_neighbors", 15),
            n_components=best_params.get("n_components", 5),
            min_dist=0.0,
            metric="cosine",
            random_state=42,
        )

        # nr_topics 自适应
        nr_topics = best_params.get("nr_topics", 12)
        if n_docs < 100:
            nr_topics = min(nr_topics, n_docs // 5)  # 小数据集限制主题数
            if nr_topics < 3:
                nr_topics = "auto"

        bertopic_kwargs: dict = dict(
            embedding_model=embedding_model,
            vectorizer_model=vectorizer,
            umap_model=umap_model,
            hdbscan_model=hdbscan_model,
            nr_topics=nr_topics,
            calculate_probabilities=False,
            verbose=True,
        )

        logger.info("BERTopic: 开始训练（nr_topics=%s, mcs=%d, n_docs=%d）...",
                     str(nr_topics), mcs, n_docs)

        topic_model = BERTopic(**bertopic_kwargs)
        topics, _ = topic_model.fit_transform(docs)

        _t_fit = _time.monotonic()
        _fit_secs = _t_fit - _t_start

        num_topics = len(set(topics)) - (1 if -1 in topics else 0)
        if num_topics == 0:
            logger.warning("BERTopic: 未能发现任何主题")
            return 0

        logger.info("BERTopic: 发现 %d 个主题（训练耗时 %.1f 秒）", num_topics, _fit_secs)

        # 4. 计算评估指标
        _t_eval = _time.monotonic()
        diversity = self._compute_topic_diversity(topic_model)
        npmi = self._compute_npmi(topic_model, docs)
        per_topic_cv = self._compute_bertopic_cv_coherence(topic_model, docs)
        _t_eval_done = _time.monotonic()
        logger.info("BERTopic: 评估完成 — diversity=%.4f npm=%.4f c_v_topics=%d (%.1fs)",
                     diversity, npmi, len(per_topic_cv), _t_eval_done - _t_eval)

        # 5. 获取主题信息
        topic_info = topic_model.get_topic_info()
        outlier_count = int(topic_info[topic_info["Topic"] == -1]["Count"].values[0]) if -1 in topics else 0
        logger.info("BERTopic: 主题分布 — outlier=%d 条, 最大主题=%d 条, 最小主题=%d 条",
                     outlier_count,
                     int(topic_info[topic_info["Topic"] != -1]["Count"].max()),
                     int(topic_info[topic_info["Topic"] != -1]["Count"].min()))

        # 5. 清除旧的 BERTopic 数据
        await self._clear_old_method_data("bertopic")

        # 6. 持久化主题和关键词（先存规则标签，再批量 LLM 精炼）
        topic_map: dict[int, Topic] = {}  # bertopic_topic_id -> Topic ORM
        topic_data_for_llm: list[dict] = []  # 供批量 LLM 调用

        for _, row in topic_info.iterrows():
            bert_topic_id = int(row["Topic"])
            if bert_topic_id == -1:
                continue  # 跳过 outlier 主题

            top_words = topic_model.get_topic(bert_topic_id)
            if not top_words:
                continue

            # 生成关键词拼接标签（Top 3）
            label = " · ".join(w for w, _ in top_words[:3])

            # 生成业务主题标签（Top 10）
            business_label = TopicLabelGenerator.generate(
                [(w, float(p), i + 1) for i, (w, p) in enumerate(top_words[:10])]
            )

            doc_count = int(row["Count"])
            logger.info("BERTopic: [Topic %d] %s | %s | %d docs",
                         bert_topic_id, business_label, label, doc_count)

            # 领域建议
            domain_hint = self._get_domain_hint(
                [(w, float(p), i + 1) for i, (w, p) in enumerate(top_words[:10])]
            )

            # 该主题的 c_v coherence（如有）
            topic_cv = per_topic_cv.get(bert_topic_id)

            # 先用规则标签写入
            topic = Topic(
                method="bertopic",
                topic_index=bert_topic_id,
                label=label,
                business_label=business_label,
                coherence_score=topic_cv,  # c_v coherence per topic
                silhouette_score=npmi,     # 复用字段存储 NPMI
                business_label_llm=None,
                business_label_confidence=1.0,
                needs_review=False,
            )
            self.db.add(topic)
            await self.db.flush()
            topic_map[bert_topic_id] = topic

            # 持久化关键词
            for rank, (word, weight) in enumerate(top_words[:10], start=1):
                self.db.add(
                    TopicKeyword(
                        topic_id=topic.id,
                        word=word,
                        weight=float(weight),
                        rank=rank,
                    )
                )

            # 收集 LLM 标注数据
            rep_comments = TopicService._get_topic_rep_comments(
                bert_topic_id, topics_list, docs, 3
            )
            topic_data_for_llm.append({
                "topic_index": bert_topic_id,
                "keywords": [w for w, _ in top_words[:15]],
                "comments": rep_comments,
                "rule_label": business_label,
                "coherence_score": topic_cv or 0.0,
                "domain_hint": domain_hint,
            })

        # 批量 LLM 精炼
        await self._apply_llm_batch_labels(topic_data_for_llm, topic_map)

        # 7. 持久化文档-主题分配
        for doc_idx, bt_topic_id in enumerate(topics):
            if bt_topic_id == -1 or bt_topic_id not in topic_map:
                continue
            self.db.add(
                DocTopic(
                    comment_id=comment_ids[doc_idx],
                    topic_id=topic_map[bt_topic_id].id,
                    probability=1.0,  # BERTopic 硬分配
                    is_primary=True,
                )
            )

        await self.db.commit()

        _t_total = _time.monotonic()
        logger.info("BERTopic: 完成 — %d 个主题, %d 条评论已分配（总耗时 %.1f 秒, 持久化 %.1f 秒）",
                     len(topic_map), sum(1 for t in topics if t != -1 and t in topic_map),
                     _t_total - _t_start, _t_total - _t_fit)
        return len(topic_map)

    async def get_topics(self, method: str = "lda") -> list[dict[str, Any]]:
        """获取指定方法的所有主题及关键词。

        Args:
            method: 主题建模方法（lda / bertopic / hdbscan）

        Returns:
            [{topic_id, topic_index, label, coherence_score,
              keywords: [{word, weight, rank}, ...], doc_count: int}, ...]
        """
        # 查询主题
        result = await self.db.execute(
            select(Topic).where(Topic.method == method).order_by(Topic.topic_index)
        )
        topics = result.scalars().all()

        output = []
        for topic in topics:
            # 查询该主题下的关键词
            kw_result = await self.db.execute(
                select(TopicKeyword)
                .where(TopicKeyword.topic_id == topic.id)
                .order_by(TopicKeyword.rank)
            )
            keywords = kw_result.scalars().all()

            # 查询分配到该主题的文档数
            doc_count_result = await self.db.execute(
                select(DocTopic).where(
                    DocTopic.topic_id == topic.id, DocTopic.is_primary.is_(True)
                )
            )
            doc_count = len(doc_count_result.scalars().all())

            # 查询代表性评论（该主题下 probability 最高的前 5 条）
            rep_result = await self.db.execute(
                select(Comment.content, DocTopic.probability)
                .join(Comment, Comment.id == DocTopic.comment_id)
                .where(
                    DocTopic.topic_id == topic.id,
                    DocTopic.is_primary.is_(True),
                    Comment.content.isnot(None),
                )
                .order_by(DocTopic.probability.desc())
                .limit(5)
            )
            representative_comments = [
                row[0] for row in rep_result.all() if row[0]
            ]

            output.append({
                "topic_id": topic.id,
                "topic_index": topic.topic_index,
                "label": topic.label or f"主题 {topic.topic_index + 1}",
                "business_label": topic.business_label,
                "business_label_llm": topic.business_label_llm,
                "business_label_confidence": topic.business_label_confidence,
                "needs_review": topic.needs_review,
                "coherence_score": round(topic.coherence_score, 4) if topic.coherence_score else None,
                "npmi_score": round(topic.silhouette_score, 4) if topic.silhouette_score else None,
                "keywords": [
                    {"word": kw.word, "weight": round(kw.weight, 4), "rank": kw.rank}
                    for kw in keywords
                ],
                "doc_count": doc_count,
                "representative_comments": representative_comments,
            })

        return output

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _get_topic_rep_comments(
        topic_id: int,
        topics_list: list[int],
        docs: list[str],
        max_count: int = 3,
    ) -> list[str]:
        """获取某主题的代表性评论（从原始文档中采样）。

        Args:
            topic_id: BERTopic 主题 ID
            topics_list: 每个文档的主题分配列表
            docs: 原始文档列表
            max_count: 最多返回几条

        Returns:
            代表性评论文本列表
        """
        comments = [
            docs[i] for i, t in enumerate(topics_list) if t == topic_id
        ]
        # 取最长的几条（通常包含更多信息）
        comments.sort(key=len, reverse=True)
        # 将空格连接的 token 还原为可读中文
        return [c.replace(" ", "") for c in comments[:max_count]]

    # ------------------------------------------------------------------
    # BERTopic 评估指标
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_topic_diversity(topic_model, top_n: int = 10) -> float:
        """计算 BERTopic 主题多样性。

        定义: top-N 关键词去重比例 = 1 - (重复词数 / 总词数)。
        值越高表示主题间关键词重叠越少，主题越独立。

        Returns:
            0.0 ~ 1.0 的多样性分数
        """
        try:
            info = topic_model.get_topic_info()
            all_words: list[str] = []
            for _, row in info.iterrows():
                topic_id = int(row["Topic"])
                if topic_id == -1:
                    continue
                words = topic_model.get_topic(topic_id)
                if words:
                    all_words.extend(w for w, _ in words[:top_n])

            if not all_words:
                return 0.0

            unique = len(set(all_words))
            diversity = unique / len(all_words)
            logger.info("BERTopic Diversity: %.4f (unique=%d, total=%d)", diversity, unique, len(all_words))
            return round(diversity, 4)
        except Exception as e:
            logger.warning("计算 topic_diversity 失败: %s", e)
            return 0.0

    @staticmethod
    def _compute_npmi(topic_model, docs: list[str], top_n: int = 10) -> float:
        """计算 BERTopic 主题的 NPMI 分数。

        使用 BERTopic 内置的 topic coherence 能力（基于归一化点互信息）。
        如果 BERTopic 版本不支持，回退到手动计算。

        Returns:
            NPMI 分数（越高越好，典型值 -1 ~ 1）
        """
        try:
            # BERTopic >= 0.15 支持 get_topic_info 返回 coherence
            # 尝试使用内置的 MPMI/NPMI
            if hasattr(topic_model, 'topic_coherence'):
                coherence_scores = topic_model.topic_coherence
                if coherence_scores:
                    valid = [s for s in coherence_scores if s is not None]
                    if valid:
                        npmi = float(np.mean(valid))
                        logger.info("BERTopic NPMI: %.4f (built-in, %d topics)", npmi, len(valid))
                        return round(npmi, 4)

            # Fallback: 基于滑动窗口手动计算
            logger.info("BERTopic 内置 coherence 不可用，使用近似 NPMI...")
            return TopicService._compute_npmi_manual(topic_model, docs, top_n)
        except Exception as e:
            logger.warning("计算 NPMI 失败: %s", e)
            return 0.0

    @staticmethod
    def _compute_npmi_manual(topic_model, docs: list[str], top_n: int = 10, window: int = 10) -> float:
        """手动计算 NPMI（近似）。

        对每个主题的 top-N 关键词，在文档滑动窗口中统计共现，
        计算归一化点互信息。

        Returns:
            近似 NPMI 分数
        """
        import math
        from collections import Counter

        # 获取所有主题的 top 关键词
        info = topic_model.get_topic_info()
        all_topic_words: list[list[str]] = []
        for _, row in info.iterrows():
            topic_id = int(row["Topic"])
            if topic_id == -1:
                continue
            words = topic_model.get_topic(topic_id)
            if words:
                all_topic_words.append([w for w, _ in words[:top_n]])

        if not all_topic_words:
            return 0.0

        # 将文档切分为 token 列表，统计词频和共现
        doc_tokens = [d.split() for d in docs]
        word_freq: Counter = Counter()
        cooccur: Counter = Counter()

        for tokens in doc_tokens:
            unique_in_doc = set(tokens)
            word_freq.update(unique_in_doc)
            token_list = list(tokens)
            for i, w1 in enumerate(token_list):
                for j in range(i + 1, min(i + window + 1, len(token_list))):
                    w2 = token_list[j]
                    if w1 < w2:
                        cooccur[(w1, w2)] += 1
                    else:
                        cooccur[(w2, w1)] += 1

        total_docs = len(docs)

        # 对每个主题计算 NPMI
        npmi_scores: list[float] = []
        for topic_words in all_topic_words:
            topic_npmi: list[float] = []
            for i, w1 in enumerate(topic_words):
                for w2 in topic_words[i + 1 :]:
                    c_xy = cooccur.get((w1, w2), 0) if w1 < w2 else cooccur.get((w2, w1), 0)
                    c_x = word_freq.get(w1, 0)
                    c_y = word_freq.get(w2, 0)

                    if c_x == 0 or c_y == 0 or c_xy == 0:
                        continue

                    pmi = math.log((c_xy * total_docs) / (c_x * c_y))
                    npmi_val = pmi / (-math.log(c_xy / total_docs)) if c_xy > 0 else 0
                    topic_npmi.append(max(-1.0, min(1.0, npmi_val)))

            if topic_npmi:
                npmi_scores.append(float(np.mean(topic_npmi)))

        result = float(np.mean(npmi_scores)) if npmi_scores else 0.0
        logger.info("BERTopic NPMI (manual): %.4f (%d topics)", result, len(npmi_scores))
        return round(result, 4)

    @staticmethod
    def _compute_bertopic_cv_coherence(
        topic_model, docs: list[str]
    ) -> dict[int, float]:
        """按主题拆分文档，用 Gensim CoherenceModel 计算 c_v 一致性。

        为每个 topic 单独建立 Gensim Corpus，计算每个 topic 的 c_v 值。
        这使得 BERTopic 也有可与 LDA 对比的 coherence_score。

        Returns:
            {topic_id: c_v_coherence_score, ...}
        """
        try:
            topics = topic_model.topics_
            if topics is None:
                return {}

            # 按主题分组文档
            topic_docs: dict[int, list[list[str]]] = defaultdict(list)
            for doc, topic_id in zip(docs, topics):
                if topic_id != -1:
                    topic_docs[topic_id].append(doc.split())

            per_topic_cv: dict[int, float] = {}
            for topic_id, texts in topic_docs.items():
                if len(texts) < 3:
                    continue
                try:
                    dictionary = Dictionary(texts)
                    # 小主题放宽过滤条件
                    dictionary.filter_extremes(no_below=1, no_above=0.9)
                    if len(dictionary) < 2:
                        continue
                    bow = [dictionary.doc2bow(t) for t in texts]
                    # 训练单主题 LDA 以评估
                    lda = LdaModel(
                        bow, num_topics=1, id2word=dictionary,
                        passes=5, random_state=42,
                    )
                    cm = CoherenceModel(
                        model=lda, texts=texts,
                        dictionary=dictionary, coherence="c_v",
                    )
                    score = float(cm.get_coherence())
                    per_topic_cv[topic_id] = score
                except Exception:
                    continue

            if per_topic_cv:
                avg = float(np.mean(list(per_topic_cv.values())))
                logger.info("BERTopic c_v coherence: avg=%.4f (%d topics)", avg, len(per_topic_cv))
            return per_topic_cv
        except Exception as e:
            logger.warning("计算 BERTopic c_v coherence 失败: %s", e)
            return {}

    async def _bertopic_grid_search(self, docs: list[str]) -> dict:
        """BERTopic 参数网格搜索。

        对 UMAP/HDBSCAN/nr_topics 的关键参数组合进行搜索，
        使用综合得分（NPMI + diversity - dominance_penalty）选择最优参数。

        Returns:
            {'nr_topics': int, 'n_neighbors': int, 'n_components': int,
             'min_cluster_size': int, 'score': float}
        """
        import time as _time
        from app.config import settings
        from sklearn.feature_extraction.text import CountVectorizer
        from bertopic import BERTopic
        from hdbscan import HDBSCAN
        from umap import UMAP

        embedding_model = self._create_embedding_model(settings)
        if embedding_model is None:
            logger.warning("Grid Search: Embedding 模型不可用，使用默认参数")
            return {"nr_topics": 12, "n_neighbors": 15, "n_components": 5,
                    "min_cluster_size": 25, "score": 0.0}

        n_docs = len(docs)
        vectorizer = CountVectorizer(
            tokenizer=lambda x: x.split(), lowercase=False,
            max_df=1.0 if n_docs < 200 else 0.7,
            min_df=1 if n_docs < 200 else 2,
            max_features=min(3000, n_docs * 20),
        )

        # 精简搜索空间（避免过长耗时）
        grid = [
            {"nr_topics": nr, "n_neighbors": nn, "n_components": nc, "min_cluster_size": mc}
            for nr in [10, 12, 15]
            for nn in [15]
            for nc in [5]
            for mc in [20, 25]
        ]

        best_result = {"nr_topics": 12, "n_neighbors": 15, "n_components": 5,
                       "min_cluster_size": 25, "score": -999.0}

        logger.info("BERTopic Grid Search: %d 个参数组合...", len(grid))

        for i, params in enumerate(grid):
            _t0 = _time.monotonic()
            try:
                hdbscan_model = HDBSCAN(
                    min_cluster_size=params["min_cluster_size"],
                    min_samples=max(5, params["min_cluster_size"] // 3),
                    metric="euclidean",
                    cluster_selection_method="eom",
                    prediction_data=True,
                )
                umap_model = UMAP(
                    n_neighbors=params["n_neighbors"],
                    n_components=params["n_components"],
                    min_dist=0.0, metric="cosine", random_state=42,
                )

                model = BERTopic(
                    embedding_model=embedding_model,
                    vectorizer_model=vectorizer,
                    umap_model=umap_model,
                    hdbscan_model=hdbscan_model,
                    nr_topics=params["nr_topics"],
                    calculate_probabilities=False,
                    verbose=False,
                )
                topics, _ = model.fit_transform(docs)
                num_topics = len(set(topics)) - (1 if -1 in topics else 0)

                if num_topics < 3:
                    logger.info("  [%d/%d] nr_topics=%d → %d topics (太少，跳过)",
                                i + 1, len(grid), params["nr_topics"], num_topics)
                    continue

                # 计算指标
                diversity = self._compute_topic_diversity(model)
                npmi = self._compute_npmi(model, docs)

                # 主题支配度惩罚（防止一个主题占比过大）
                topic_counts = Counter(t for t in topics if t != -1)
                max_ratio = max(topic_counts.values()) / len(topics) if topic_counts else 1.0
                dominance_penalty = max(0.0, (max_ratio - 0.6) * 2.0)

                score = 0.4 * npmi + 0.3 * diversity - 0.3 * dominance_penalty

                _elapsed = _time.monotonic() - _t0
                logger.info("  [%d/%d] nr_topics=%d n_comp=%d mcs=%d → %d topics | "
                            "npmi=%.3f div=%.3f dom=%.3f score=%.3f (%.1fs)",
                            i + 1, len(grid), params["nr_topics"],
                            params["n_components"], params["min_cluster_size"],
                            num_topics, npmi, diversity, max_ratio, score, _elapsed)

                if score > best_result["score"]:
                    best_result = {**params, "score": score}

            except Exception as e:
                logger.warning("  [%d/%d] 参数组合失败: %s", i + 1, len(grid), e)
                continue

        logger.info("Grid Search 最优: %s", best_result)
        return best_result

    # ------------------------------------------------------------------
    # 私有方法
    # ------------------------------------------------------------------

    def _compute_per_topic_coherence(
        self, model: LdaModel, texts: list[list[str]], dictionary: Dictionary
    ) -> dict[int, float]:
        """计算每个主题的独立一致性分数。

        使用 Gensim CoherenceModel 的 per_topic 模式，
        避免所有主题共享同一全局平均值。

        Returns:
            {topic_idx: coherence_score, ...}
        """
        try:
            coherence_model = CoherenceModel(
                model=model,
                texts=texts,
                dictionary=dictionary,
                coherence="c_v",
            )
            per_topic = coherence_model.get_coherence_per_topic()
            return {idx: float(score) for idx, score in enumerate(per_topic)}
        except Exception as e:
            logger.warning("无法计算 per-topic coherence: %s，回退到全局值", e)
            return {}

    def _save_model(self, model: LdaModel, dictionary: Dictionary) -> None:
        """将训练好的 LDA 模型和词典保存到磁盘供预测服务加载。"""
        from app.config import settings as app_settings

        model_dir = app_settings.data_dir / "model"
        model_dir.mkdir(parents=True, exist_ok=True)

        model.save(str(model_dir / "lda_model"))
        dictionary.save(str(model_dir / "lda_dictionary"))
        logger.info("LDA 模型已保存至 %s", model_dir)

    @staticmethod
    def load_model(data_dir: Path) -> tuple[LdaModel, Dictionary] | None:
        """从磁盘加载 LDA 模型和词典。

        Returns:
            (LdaModel, Dictionary) 或 None
        """
        model_path = data_dir / "model" / "lda_model"
        dict_path = data_dir / "model" / "lda_dictionary"
        if not model_path.exists() or not dict_path.exists():
            logger.warning("LDA 模型文件不存在，无法加载")
            return None
        try:
            model = LdaModel.load(str(model_path))
            dictionary = Dictionary.load(str(dict_path))
            return model, dictionary
        except Exception as e:
            logger.error("加载 LDA 模型失败: %s", e)
            return None

    @staticmethod
    def _create_embedding_model(app_settings):
        """创建 SentenceTransformer Embedding 模型 — 3 层策略。

        Layer 1: 本地模型路径（GC_BERTOPIC_MODEL_PATH 或默认 bge-small-zh-v1.5）
        Layer 2: HuggingFace 自动下载（bertopic_model_name）→ 缓存至本地
        Layer 3: 返回 None → 调用方使用 TF-IDF fallback

        日志输出: 模型路径、是否本地加载、Embedding 维度。
        """
        import time as _time

        from sentence_transformers import SentenceTransformer

        model_name = app_settings.bertopic_model_name
        local_path = app_settings.resolve_bertopic_model_path()

        logger.info("BERTopic Embedding: model_name=%s", model_name)
        logger.info("BERTopic Embedding: local_path=%s", local_path)
        logger.info("BERTopic Embedding: local_path exists=%s, config.json=%s",
                     local_path.exists(),
                     (local_path / "config.json").exists() if local_path.exists() else False)

        # Layer 1: 本地模型路径
        if local_path.exists() and (local_path / "config.json").exists():
            _t0 = _time.monotonic()
            logger.info("BERTopic Embedding: 从本地加载 %s ...", local_path)
            try:
                model = SentenceTransformer(str(local_path), device="cpu")
                dim = model.get_sentence_embedding_dimension() if hasattr(model, "get_sentence_embedding_dimension") else model.get_embedding_dimension()
                _elapsed = _time.monotonic() - _t0
                logger.info("BERTopic Embedding: ✅ 本地加载成功 | 路径=%s | dim=%d | 耗时=%.1fs",
                             local_path, dim, _elapsed)
                return model
            except Exception as e:
                logger.warning("BERTopic Embedding: 本地加载失败 (%s)，尝试下载...", e)

        # Layer 2: HuggingFace 自动下载 → 保存至 local_path
        try:
            _t0 = _time.monotonic()
            logger.info("BERTopic Embedding: 下载模型 %s（首次 ~400MB，需代理）...", model_name)
            model = SentenceTransformer(model_name, device="cpu")
            dim = model.get_sentence_embedding_dimension() if hasattr(model, "get_sentence_embedding_dimension") else model.get_embedding_dimension()
            _elapsed = _time.monotonic() - _t0
            logger.info("BERTopic Embedding: ✅ 下载成功 | model=%s | dim=%d | 耗时=%.1fs",
                         model_name, dim, _elapsed)
            # 缓存到本地
            local_path.parent.mkdir(parents=True, exist_ok=True)
            model.save(str(local_path))
            logger.info("BERTopic Embedding: 已缓存至 %s", local_path)
            return model
        except Exception as e:
            logger.warning(
                "BERTopic Embedding: ❌ 不可用 (%s)。将使用 TF-IDF fallback。"
                "手动下载: git clone https://huggingface.co/BAAI/bge-small-zh-v1.5",
                e,
            )
            return None

    def compute_topic_separation(
        self, model: LdaModel, num_topics: int
    ) -> dict[str, Any]:
        """评估主题分离度。

        计算:
        1. 主题间 Jensen-Shannon 散度矩阵
        2. 主题重叠词比例（相邻主题 Top-N 关键词的交集比例）

        Returns:
            {js_divergence_matrix, overlap_ratio}
        """
        # 1. JS 散度矩阵
        topic_distributions = []
        for topic_idx in range(num_topics):
            dist = model.get_topic_terms(topic_idx, topn=len(model.id2word))
            # 构建完整词分布向量（按词典顺序）
            word_probs = np.zeros(len(model.id2word))
            for word_id, prob in dist:
                if word_id < len(word_probs):
                    word_probs[word_id] = prob
            topic_distributions.append(word_probs)

        js_matrix = np.zeros((num_topics, num_topics))
        for i in range(num_topics):
            for j in range(i + 1, num_topics):
                # JS 散度 = sqrt(JS distance)，值越大表示主题越不同
                js_dist = jensenshannon(topic_distributions[i], topic_distributions[j])
                js_matrix[i][j] = float(js_dist)
                js_matrix[j][i] = float(js_dist)

        # 2. 主题重叠词比例
        top_n = 10
        topic_words = []
        for topic_idx in range(num_topics):
            words = {w for w, _ in model.show_topic(topic_idx, topn=top_n)}
            topic_words.append(words)

        overlap_ratios = []
        for i in range(num_topics - 1):
            overlap = len(topic_words[i] & topic_words[i + 1]) / top_n
            overlap_ratios.append(round(overlap, 3))

        return {
            "js_divergence": js_matrix.tolist(),
            "overlap_ratio": overlap_ratios,
            "average_overlap": round(np.mean(overlap_ratios), 3) if overlap_ratios else 0,
        }

    # ------------------------------------------------------------------
    # LLM 批量标签精炼辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _get_domain_hint(
        keywords: list[tuple[str, float, int]],
    ) -> str:
        """获取领域建议（来自 TopicLabelGenerator 的 top-2 匹配）。

        Args:
            keywords: [(word, weight, rank), ...]

        Returns:
            "领域1, 领域2" 或 "未识别"
        """
        try:
            domain_scores = TopicLabelGenerator._score_domains(keywords)
            if not domain_scores:
                return "未识别"
            sorted_domains = sorted(
                domain_scores.items(), key=lambda x: x[1], reverse=True
            )
            top = [d for d, s in sorted_domains[:2] if s > 0.05]
            return ", ".join(top) if top else "未识别"
        except Exception:
            return "未识别"

    async def _apply_llm_batch_labels(
        self,
        topic_data: list[dict],
        topic_map: dict[int, "Topic"],
    ) -> None:
        """批量调用 LLM 精炼标签，并更新 Topic 记录。

        Args:
            topic_data: 主题信息列表（来自 run_lda / run_bertopic）
            topic_map: {topic_index: Topic ORM} 映射
        """
        if not topic_data:
            return

        try:
            from app.services.llm_labeler import LLMLabeler

            labeler = LLMLabeler()
            is_healthy = await labeler.health_check()

            if not is_healthy:
                logger.info("Ollama 不可用，跳过 LLM 批量精炼")
                await labeler.close()
                return

            results = await labeler.refine_batch(topic_data)
            await labeler.close()

            # 更新 Topic 记录
            for r in results:
                topic_idx = r["topic_index"]
                tm = topic_map.get(topic_idx)
                if tm is None:
                    continue

                llm_label = r["label"]
                confidence = r["confidence"]
                needs_review = r.get("needs_review", False)

                tm.business_label = llm_label
                tm.business_label_confidence = confidence
                tm.needs_review = needs_review

                # 如果 LLM 标签与规则标签不同，记录 LLM 版本
                if llm_label != tm.business_label:
                    tm.business_label_llm = llm_label

                logger.info(
                    "LLM 精炼 [topic %d]: conf=%.2f review=%s → '%s'",
                    topic_idx, confidence, needs_review, llm_label,
                )

            await self.db.flush()

        except Exception as e:
            logger.warning("LLM 批量精炼失败: %s，保留规则标签", e)

    async def relabel_topics(self, method: str = "lda") -> list[dict]:
        """对已有主题重新运行 LLM 精炼（供 API 触发）。

        从数据库加载指定 method 的 Topic + TopicKeyword，
        构造信息列表，调用 refine_batch()，更新 Topic 记录。

        Args:
            method: 主题建模方法

        Returns:
            精炼结果列表
        """
        # 1. 查询已有主题及关键词
        topic_result = await self.db.execute(
            select(Topic).where(
                Topic.method == method,
                Topic.topic_index >= 0,
            ).order_by(Topic.topic_index)
        )
        topics = topic_result.scalars().all()

        if not topics:
            logger.warning("relabel_topics: method=%s 无主题", method)
            return []

        # 2. 收集每个主题的信息
        topic_data: list[dict] = []
        topic_map: dict[int, Topic] = {}

        for topic in topics:
            kw_result = await self.db.execute(
                select(TopicKeyword.word, TopicKeyword.weight, TopicKeyword.rank)
                .where(TopicKeyword.topic_id == topic.id)
                .order_by(TopicKeyword.rank)
            )
            keywords = [(row[0], float(row[1]), row[2]) for row in kw_result.all()]

            topic_map[topic.topic_index] = topic

            # 获取代表性评论
            rep = await self._get_representative_comments_for_topic(
                topic.id, limit=3
            )

            rule_label = topic.business_label or ""

            topic_data.append({
                "topic_index": topic.topic_index,
                "keywords": [w for w, _, _ in keywords[:15]],
                "comments": rep,
                "rule_label": rule_label,
                "coherence_score": topic.coherence_score or 0.0,
                "domain_hint": self._get_domain_hint(keywords[:10]),
            })

        # 3. 批量 LLM 精炼
        await self._apply_llm_batch_labels(topic_data, topic_map)
        await self.db.commit()

        # 4. 构造返回
        results = []
        for topic in topics:
            await self.db.refresh(topic)
            results.append({
                "topic_index": topic.topic_index,
                "before": topic.business_label or "",
                "label": topic.business_label or "",
                "confidence": topic.business_label_confidence or 1.0,
                "needs_review": topic.needs_review or False,
                "from_cache": False,
            })

        return results

    async def get_topics_needing_review(self, method: str = "lda") -> list[dict]:
        """列出置信度低、需要人工审核的主题。

        Args:
            method: 主题建模方法

        Returns:
            [{topic_id, topic_index, business_label, confidence, coherence_score}, ...]
        """
        result = await self.db.execute(
            select(Topic).where(
                Topic.method == method,
                Topic.needs_review == True,  # noqa: E712
            ).order_by(Topic.business_label_confidence)
        )
        topics = result.scalars().all()

        return [
            {
                "topic_id": t.id,
                "topic_index": t.topic_index,
                "business_label": t.business_label,
                "confidence": t.business_label_confidence,
                "coherence_score": t.coherence_score,
            }
            for t in topics
        ]

    async def _get_representative_comments_for_topic(
        self, topic_id: int, limit: int = 3
    ) -> list[str]:
        """获取某主题的代表性评论（按概率降序）。

        Args:
            topic_id: Topic ORM id
            limit: 返回数量

        Returns:
            评论原文列表
        """
        result = await self.db.execute(
            select(Comment.cleaned_content)
            .join(DocTopic, DocTopic.comment_id == Comment.id)
            .where(
                DocTopic.topic_id == topic_id,
                DocTopic.is_primary == True,  # noqa: E712
                Comment.cleaned_content.isnot(None),
            )
            .order_by(DocTopic.probability.desc())
            .limit(limit)
        )
        return [row[0] or "" for row in result.all()]

    async def _clear_old_lda_data(self) -> None:
        """清除旧的 LDA 数据（主题、关键词、文档分配）。"""
        await self._clear_old_method_data("lda")

    async def _clear_old_method_data(self, method: str) -> None:
        """清除指定建模方法的旧数据。"""
        result = await self.db.execute(
            select(Topic.id).where(Topic.method == method)
        )
        old_ids = [row[0] for row in result.all()]
        if old_ids:
            await self.db.execute(
                delete(DocTopic).where(DocTopic.topic_id.in_(old_ids))
            )
            await self.db.execute(
                delete(TopicKeyword).where(TopicKeyword.topic_id.in_(old_ids))
            )
            await self.db.execute(
                delete(Topic).where(Topic.id.in_(old_ids))
            )
            await self.db.flush()
