"""
LLM 主题标签精炼服务

使用本地 Ollama 模型对规则引擎生成的候选标签进行精炼和去歧义，
提升主题名称的可解释性和准确性。

v2:
- 批量标注 (refine_batch)：一次 LLM 调用处理所有主题
- LLMCache：基于 SHA256 的内存缓存，避免冗余调用
- 组合置信度：语义相似度 + 加权关键词重叠 + 字符 Jaccard
- 增强 Prompt：领域建议 + coherence 质量分级 + 结构化输出
"""

import hashlib
import json
import logging
import time as _time
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# ---- 批量主题命名 Prompt 模板 ----
BATCH_NAMING_PROMPT = """为以下 {n_topics} 个考研主题生成简洁中文名称（4-8字）。如果候选标签合理则直接返回。

{topics_section}

只返回编号和名称：
0: 名称
1: 名称
..."""

SINGLE_TOPIC_TEMPLATE = """主题 {idx}:
关键词: {keywords}
评论: {comment_1} {comment_2}
候选: {rule_label} | 领域: {domain_hint} | 质量: {quality_tier}
---"""


def _quality_tier(coherence: float) -> str:
    """将 coherence 分数映射到质量分级。"""
    if coherence >= 0.5:
        return "excellent"
    elif coherence >= 0.4:
        return "good"
    elif coherence >= 0.3:
        return "fair"
    return "poor"


# ---- 内存缓存 ----

class LLMCache:
    """LLM 标签结果的内存缓存。

    缓存 key 基于 (keywords, rule_label, coherence) 的 SHA256 哈希。
    """

    def __init__(self, ttl_hours: int = 24):
        self._store: dict[str, tuple[str, datetime]] = {}
        self._ttl = timedelta(hours=ttl_hours)
        self._hits = 0
        self._misses = 0

    def _make_key(
        self, keywords: list[str], rule_label: str, coherence: float
    ) -> str:
        """生成缓存 key。"""
        payload = json.dumps(
            {
                "kw": sorted(keywords[:15]),
                "rl": rule_label,
                "coh": round(coherence, 4),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def get(self, keywords: list[str], rule_label: str, coherence: float) -> str | None:
        """查缓存，命中返回标签，未命中返回 None。"""
        if not settings.llm_cache_enabled:
            return None
        key = self._make_key(keywords, rule_label, coherence)
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None
        label, timestamp = entry
        if datetime.now(timezone.utc) - timestamp > self._ttl:
            del self._store[key]
            self._misses += 1
            return None
        self._hits += 1
        return label

    def set(
        self, keywords: list[str], rule_label: str, coherence: float, label: str
    ) -> None:
        """写入缓存。"""
        if not settings.llm_cache_enabled:
            return
        key = self._make_key(keywords, rule_label, coherence)
        self._store[key] = (label, datetime.now(timezone.utc))

    def clear(self) -> int:
        """清空缓存，返回清除的条目数。"""
        count = len(self._store)
        self._store.clear()
        self._hits = 0
        self._misses = 0
        logger.info("LLM 缓存已清空 (%d 条)", count)
        return count

    def stats(self) -> dict:
        """返回缓存统计。"""
        total = self._hits + self._misses
        return {
            "size": len(self._store),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total, 3) if total > 0 else 0.0,
        }


# ---- 全局缓存单例 ----
_global_cache: Optional[LLMCache] = None


def get_cache() -> LLMCache:
    """获取全局 LLM 缓存单例。"""
    global _global_cache
    if _global_cache is None:
        _global_cache = LLMCache(ttl_hours=settings.llm_cache_ttl_hours)
    return _global_cache


# ---- LLMLabeler v2 ----

class LLMLabeler:
    """使用本地 LLM 精炼主题标签 (v2: 批量标注 + 缓存 + 组合置信度)。

    用法:
        labeler = LLMLabeler()
        results = await labeler.refine_batch([
            {
                "topic_index": 0,
                "keywords": ["数学", "概率论", "茆诗松"],
                "comments": ["茆诗松的概率论好难", "数理统计怎么复习"],
                "rule_label": "数学复习",
                "coherence_score": 0.45,
                "domain_hint": "数学复习, 专业课",
            },
            ...
        ])
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.timeout = timeout if timeout is not None else settings.ollama_timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._cache = get_cache()

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 httpx 客户端。"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        """关闭 HTTP 客户端。"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> bool:
        """检查 Ollama 服务是否可用。"""
        try:
            client = await self._get_client()
            resp = await client.get(f"{self.base_url}/api/tags")
            return resp.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # 批量标注 (v2 核心)
    # ------------------------------------------------------------------

    async def refine_batch(
        self, topics: list[dict]
    ) -> list[dict[str, str | float | bool]]:
        """批量精炼主题标签。

        Args:
            topics: 主题信息列表，每项包含:
                - topic_index (int)
                - keywords (list[str]): Top-15 关键词
                - comments (list[str]): 代表性评论（最多 3 条）
                - rule_label (str): 规则引擎候选标签
                - coherence_score (float): 一致性分数
                - domain_hint (str): 领域建议（来自 TopicLabelGenerator）

        Returns:
            精炼结果列表，每项包含:
                - topic_index (int)
                - label (str): 精炼后的标签
                - confidence (float): 置信度 0.0~1.0
                - needs_review (bool): 是否需要人工审核
                - from_cache (bool): 是否来自缓存
        """
        if not topics:
            return []

        # 分批处理
        batch_size = settings.llm_batch_size
        all_results: list[dict] = []

        for batch_start in range(0, len(topics), batch_size):
            batch = topics[batch_start : batch_start + batch_size]
            batch_results = await self._refine_one_batch(batch)
            all_results.extend(batch_results)

        return all_results

    async def _refine_one_batch(
        self, topics: list[dict]
    ) -> list[dict]:
        """处理单批主题（≤ batch_size 个）。"""
        results: list[dict] = []
        uncached: list[tuple[int, dict]] = []  # (index_in_batch, topic)

        # 1. 先查缓存
        for i, topic in enumerate(topics):
            cached = self._cache.get(
                topic.get("keywords", []),
                topic.get("rule_label", ""),
                topic.get("coherence_score", 0.0),
            )
            if cached is not None:
                logger.debug("缓存命中: topic %d → '%s'", topic.get("topic_index"), cached)
                results.append({
                    "topic_index": topic.get("topic_index", i),
                    "label": cached,
                    "confidence": 0.85,
                    "needs_review": False,
                    "from_cache": True,
                })
            else:
                uncached.append((i, topic))

        if not uncached:
            return results

        # 2. 检查 Ollama 是否可用
        is_healthy = await self.health_check()
        if not is_healthy:
            logger.warning("Ollama 不可用，未缓存主题回退到规则标签")
            for i, topic in uncached:
                rule_label = topic.get("rule_label", "")
                results.insert(topic.get("topic_index", i), {
                    "topic_index": topic.get("topic_index", i),
                    "label": rule_label,
                    "confidence": 0.5,
                    "needs_review": False,
                    "from_cache": False,
                })
            # 按 topic_index 排序
            results.sort(key=lambda x: x.get("topic_index", 0))
            return results

        # 3. 构建 Prompt
        sections = []
        for local_idx, topic in uncached:
            _, t = local_idx, topic
            comments = t.get("comments", [])
            c1 = (comments[0][:80] + "..." if comments[0] and len(comments[0]) > 80 else (comments[0] or "（无）"))
            c2 = ""
            if len(comments) > 1:
                c2_val = comments[1] or ""
                c2 = " " + (c2_val[:80] + "..." if len(c2_val) > 80 else c2_val)
            sections.append(
                SINGLE_TOPIC_TEMPLATE.format(
                    idx=t.get("topic_index", 0),
                    keywords=", ".join(t.get("keywords", [])[:10]),
                    comment_1=c1,
                    comment_2=c2,
                    rule_label=t.get("rule_label", ""),
                    domain_hint=t.get("domain_hint", "未识别"),
                    quality_tier=_quality_tier(t.get("coherence_score", 0.0)),
                )
            )

        prompt = BATCH_NAMING_PROMPT.format(
            n_topics=len(uncached),
            topics_section="\n".join(sections),
        )

        # 4. 调用 LLM（使用 chat 端点以正确处理 qwen3 thinking 模式）
        try:
            client = await self._get_client()
            # num_predict 需足够大以容纳 thinking tokens + 实际响应
            resp = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": max(512 * len(uncached), 2048),
                    },
                },
            )

            if resp.status_code == 200:
                data = resp.json()
                llm_output = data.get("message", {}).get("content", "").strip()
                parsed = self._parse_batch_response(llm_output, len(uncached))

                for local_idx, label in parsed.items():
                    _, topic = uncached[local_idx]
                    rule_label = topic.get("rule_label", "")
                    coherence = topic.get("coherence_score", 0.0)

                    # 清理标签
                    label = self._clean_label(label)
                    if not label or len(label) < 2:
                        label = rule_label

                    # 写缓存
                    self._cache.set(
                        topic.get("keywords", []),
                        rule_label,
                        coherence,
                        label,
                    )

                    # 计算置信度
                    confidence = self._compute_confidence_v2(
                        rule_label, label, topic.get("keywords", [])
                    )
                    needs_review = confidence < 0.5

                    results.append({
                        "topic_index": topic.get("topic_index", 0),
                        "label": label,
                        "confidence": confidence,
                        "needs_review": needs_review,
                        "from_cache": False,
                    })

                    logger.info(
                        "LLM 精炼 [topic %d]: '%s' → '%s' (conf=%.2f)",
                        topic.get("topic_index", 0),
                        rule_label,
                        label,
                        confidence,
                    )
            else:
                logger.warning("Ollama 返回非 200: %d", resp.status_code)
                for i, topic in uncached:
                    rule_label = topic.get("rule_label", "")
                    results.append({
                        "topic_index": topic.get("topic_index", i),
                        "label": rule_label,
                        "confidence": 0.5,
                        "needs_review": False,
                        "from_cache": False,
                    })

        except httpx.TimeoutException:
            logger.warning("LLM 批量精炼超时 (%.1fs)，回退到规则标签", self.timeout)
            for i, topic in uncached:
                rule_label = topic.get("rule_label", "")
                results.append({
                    "topic_index": topic.get("topic_index", i),
                    "label": rule_label,
                    "confidence": 0.3,
                    "needs_review": False,
                    "from_cache": False,
                })
        except Exception as e:
            logger.warning("LLM 批量精炼失败: %s，回退到规则标签", e)
            for i, topic in uncached:
                rule_label = topic.get("rule_label", "")
                results.append({
                    "topic_index": topic.get("topic_index", i),
                    "label": rule_label,
                    "confidence": 0.3,
                    "needs_review": False,
                    "from_cache": False,
                })

        # 按 topic_index 排序
        results.sort(key=lambda x: x.get("topic_index", 0))
        return results

    def _parse_batch_response(self, output: str, expected_count: int) -> dict[int, str]:
        """解析 LLM 批量响应，提取编号标签。

        期望格式:
            0: 标签A
            1: 标签B
            ...

        Returns:
            {local_index: label, ...}
        """
        parsed: dict[int, str] = {}
        lines = output.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 匹配 "数字: 标签" 或 "数字：标签"
            parts = line.split(":", 1) if ":" in line else line.split("：", 1)
            if len(parts) != 2:
                # 尝试 "数字. 标签"
                parts = line.split(".", 1)
                if len(parts) != 2:
                    continue
            try:
                idx = int(parts[0].strip())
                label = parts[1].strip()
                parsed[idx] = label
            except ValueError:
                continue

        # 如果解析数量不足，尝试回退：所有非空行作为标签
        if len(parsed) < expected_count:
            logger.info(
                "批量解析仅得到 %d/%d 个标签，尝试回退",
                len(parsed),
                expected_count,
            )
            fallback = [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]
            for i, label in enumerate(fallback):
                if i not in parsed:
                    parsed[i] = label

        return parsed

    # ------------------------------------------------------------------
    # 标签清理
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_label(label: str) -> str:
        """清理 LLM 输出的标签。"""
        # 1. 去掉引号
        for char in ['"', '"', '"', "'", "'", "'", '「', '」', '『', '』']:
            label = label.replace(char, "")
        # 2. 去掉常见前缀
        for prefix in [
            "主题名：", "主题名:", "标签：", "标签:", "主题：",
            "主题:", "主题标签：", "主题标签:", "名称：", "名称:",
        ]:
            if prefix in label:
                label = label.split(prefix)[-1].strip()
        # 3. 多行/多句 → 取最短有效行
        lines = [l.strip() for l in label.split("\n") if l.strip()]
        if lines:
            valid = [l for l in lines if 3 <= len(l) <= 12]
            if valid:
                label = min(valid, key=len)
            else:
                label = lines[0]
        # 4. 去掉句号等结束标点
        for punct in ["。", "，", "、", "！", "？", ".", ",", "!", "）", ")"]:
            label = label.rstrip(punct)
        # 5. 长度截断
        if len(label) > 12:
            label = label[:12]
        return label.strip()

    # ------------------------------------------------------------------
    # 组合置信度 (v2)
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_confidence_v2(
        rule_label: str,
        llm_label: str,
        topic_keywords: list[str],
    ) -> float:
        """组合置信度：语义 Jaccard + 加权关键词重叠 + 字符 Jaccard。

        权重:
        - 语义相似度 (字符 Jaccard 代理): 0.40
        - 加权关键词重叠: 0.35
        - 字符级完全匹配: 0.25
        """
        if not llm_label or not rule_label:
            return 0.0
        if rule_label == llm_label:
            return 1.0

        score = 0.0

        # 1. 语义相似度 (字符 Jaccard 代理，当 embedding 不可用时)
        set_r = set(rule_label)
        set_l = set(llm_label)
        if set_r and set_l:
            char_jaccard = len(set_r & set_l) / len(set_r | set_l)
            score += 0.40 * char_jaccard
        # 如果某集合为空，该分量贡献 0

        # 2. 加权关键词重叠
        score += 0.35 * LLMLabeler._weighted_keyword_overlap(
            llm_label, topic_keywords
        )

        # 3. 字符 Jaccard（与 #1 相同但保留用于完整性）
        if set_r and set_l:
            score += 0.25 * char_jaccard
        else:
            score += 0.25 * 0.0

        return round(min(1.0, max(0.0, score)), 2)

    @staticmethod
    def _weighted_keyword_overlap(
        label: str, keywords: list[str]
    ) -> float:
        """计算标签与关键词的加权重叠度。

        标签中包含排名靠前的关键词 → 更高分。
        使用指数衰减权重: rank 1 → 1.000, rank 5 → 0.401, rank 10 → 0.241

        Returns:
            归一化重叠分数 0.0~1.0
        """
        if not keywords or not label:
            return 0.0

        max_score = 0.0
        actual_score = 0.0

        for i, kw in enumerate(keywords[:10]):
            weight = 1.0 / ((i + 1) ** 0.5)  # sqrt 衰减比线性更平滑
            max_score += weight
            if kw in label:
                actual_score += weight

        return round(actual_score / max_score, 3) if max_score > 0 else 0.0

    # ------------------------------------------------------------------
    # 向后兼容: 单主题精炼（委托给 refine_batch）
    # ------------------------------------------------------------------

    async def refine(
        self,
        keywords: list[str],
        comments: list[str],
        rule_label: str,
    ) -> tuple[str, float]:
        """使用 LLM 精炼单个主题标签（向后兼容）。

        内部委托给 refine_batch()。
        """
        results = await self.refine_batch([
            {
                "topic_index": 0,
                "keywords": keywords,
                "comments": comments,
                "rule_label": rule_label,
                "coherence_score": 0.5,
                "domain_hint": "",
            }
        ])
        if results:
            r = results[0]
            return r["label"], r["confidence"]
        return rule_label, 0.3
