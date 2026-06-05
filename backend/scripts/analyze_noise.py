#!/usr/bin/env python3
"""
数据驱动噪声词分析工具

通过查询数据库中的真实数据，自动识别噪声词（标点、单字、数字、
高频无意义词、跨主题污染词等），不依赖人工指定的词表。

用法:
  python scripts/analyze_noise.py                         # 分析当前数据
  python scripts/analyze_noise.py --apply                 # 分析 + 追加停用词 + 重跑 pipeline
  python scripts/analyze_noise.py --compare               # 对比修改前后的主题质量
"""

import argparse
import json
import logging
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from math import log2
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

from sqlalchemy import create_engine, text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("analyze_noise")

# ---------------------------------------------------------------------------
# 数据库连接
# ---------------------------------------------------------------------------

DB_PATH = _BACKEND_DIR / "gradcareer.db"
STOPWORDS_PATH = _BACKEND_DIR / "data" / "merged_stopwords.txt"
SNAPSHOT_PATH = _BACKEND_DIR / "data" / "topic_snapshot.json"


def get_engine():
    return create_engine(f"sqlite:///{DB_PATH}", echo=False)


# ---------------------------------------------------------------------------
# 数据加载
# ---------------------------------------------------------------------------

def load_comments(conn):
    """加载所有评论的 tokens_json 和 id。"""
    rows = conn.execute(text(
        "SELECT id, tokens_json FROM comments WHERE tokens_json IS NOT NULL AND token_count > 0"
    )).fetchall()
    docs = []
    for cid, tj in rows:
        try:
            tokens = json.loads(tj)
            if tokens:
                docs.append({"id": cid, "tokens": tokens})
        except json.JSONDecodeError:
            continue
    return docs


def load_keywords(conn):
    """加载 keywords 表。"""
    rows = conn.execute(text(
        "SELECT word, frequency, tfidf_score FROM keywords ORDER BY frequency DESC"
    )).fetchall()
    return [{"word": r[0], "frequency": r[1], "tfidf_score": r[2] or 0.0} for r in rows]


def load_topics(conn):
    """加载 LDA 主题及关键词。"""
    topics = conn.execute(text(
        "SELECT id, topic_index, label, coherence_score FROM topics WHERE method='lda' ORDER BY topic_index"
    )).fetchall()
    result = []
    for t in topics:
        kws = conn.execute(text(
            "SELECT word, weight, rank FROM topic_keywords WHERE topic_id=:tid ORDER BY rank"
        ), {"tid": t[0]}).fetchall()
        result.append({
            "id": t[0], "topic_index": t[1], "label": t[2],
            "coherence_score": t[3] or 0.0,
            "keywords": [{"word": k[0], "weight": k[1], "rank": k[2]} for k in kws],
        })
    return result


def load_stopwords():
    """加载现有停用词集合。"""
    if not STOPWORDS_PATH.exists():
        return set()
    with open(STOPWORDS_PATH, encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip() and not line.startswith("#")}


# ---------------------------------------------------------------------------
# 噪声识别 (R1-R6)
# ---------------------------------------------------------------------------

def char_category(token: str) -> str:
    """返回 token 的字符类型分类。"""
    if not token or not token.strip():
        return "whitespace"
    if token.isdigit() or re.match(r'^\d+$', token):
        return "digit"
    cat = unicodedata.category(token[0])
    if cat.startswith("P"):
        return "punctuation"
    if cat.startswith("S"):
        return "symbol"
    if cat.startswith("Z"):
        return "whitespace"
    if len(token) == 1:
        if "一" <= token <= "鿿":
            return "single_cjk"
        if token.isascii() and (token.isalpha() or token.isdigit()):
            return "single_ascii"
        return "single_other"
    return "valid"


def r1_character_type(docs: list[dict]) -> dict[str, list[dict]]:
    """R1: 基于字符类型的确定性噪声识别。"""
    counter = Counter()
    for doc in docs:
        for t in doc["tokens"]:
            cat = char_category(t)
            if cat != "valid":
                counter[(t, cat)] += 1

    by_cat = defaultdict(list)
    for (token, cat), freq in counter.most_common():
        by_cat[cat].append({"token": token, "frequency": freq})

    return dict(by_cat)


def r2_high_doc_low_tfidf(keywords: list[dict], docs: list[dict]) -> list[dict]:
    """R2: 高文档频率 + 低 TF-IDF 比 → 无信息量高频词。"""
    total_docs = len(docs)
    if total_docs == 0:
        return []

    # 计算每个词的 TF-IDF/freq 比率
    tfidf_ratios = []
    for kw in keywords:
        tfidf = kw["tfidf_score"]
        freq = kw["frequency"]
        if freq > 0 and tfidf > 0:
            ratio = freq / tfidf
            tfidf_ratios.append(ratio)

    if not tfidf_ratios:
        return []

    tfidf_ratios.sort()
    median_ratio = tfidf_ratios[len(tfidf_ratios) // 2]
    threshold = median_ratio * 2.0

    # 计算文档频率
    candidates = []
    for kw in keywords[:300]:  # top 300 by frequency
        doc_count = sum(
            1 for doc in docs if kw["word"] in doc["tokens"]
        )
        doc_pct = doc_count / total_docs
        tfidf = kw["tfidf_score"]
        freq = kw["frequency"]
        ratio = freq / (tfidf + 0.01) if tfidf > 0 else 999

        if doc_pct > 0.12 and ratio > threshold:
            candidates.append({
                "word": kw["word"],
                "frequency": freq,
                "tfidf_score": round(tfidf, 4),
                "doc_pct": round(doc_pct, 3),
                "freq_tfidf_ratio": round(ratio, 1),
            })

    # 按比率降序排列
    candidates.sort(key=lambda x: x["freq_tfidf_ratio"], reverse=True)
    return candidates


def r3_topic_entropy(docs: list[dict], topics: list[dict]) -> list[dict]:
    """R3: 多主题均匀分布 → 无主题区分力。"""
    # 构建 comment_id -> primary_topic 映射
    conn = get_engine().connect()
    mapping = {}
    rows = conn.execute(text(
        "SELECT comment_id, topic_id FROM doc_topics WHERE is_primary=1"
    )).fetchall()
    # topic_id -> topic_index
    tid_to_idx = {}
    for t in topics:
        tid_to_idx[t["id"]] = t["topic_index"]
    for cid, tid in rows:
        if tid in tid_to_idx:
            mapping[cid] = tid_to_idx[tid]
    conn.close()

    num_topics = len(topics)
    if num_topics == 0:
        return []

    # 统计每个词在各主题中的文档分布
    word_docs = defaultdict(lambda: defaultdict(int))
    for doc in docs:
        topic_idx = mapping.get(doc["id"])
        if topic_idx is None:
            continue
        seen = set()
        for t in doc["tokens"]:
            if t not in seen:
                word_docs[t][topic_idx] += 1
                seen.add(t)

    candidates = []
    for word, dist in word_docs.items():
        if sum(dist.values()) < 5:  # 至少出现 5 次
            continue
        # 计算主题分布熵
        total = sum(dist.values())
        probs = [dist.get(i, 0) / total for i in range(num_topics)]
        entropy = -sum(p * log2(p) for p in probs if p > 0)
        max_entropy = log2(num_topics)
        normalized = entropy / max_entropy if max_entropy > 0 else 0

        if normalized > 0.75:  # 分布 ≥75% 均匀 → 无主题区分力
            candidates.append({
                "word": word,
                "total_docs": total,
                "topic_distribution": {str(k): v for k, v in dist.items()},
                "entropy": round(entropy, 3),
                "normalized_entropy": round(normalized, 3),
            })

    candidates.sort(key=lambda x: x["normalized_entropy"], reverse=True)
    return candidates


def r4_single_char_high_freq(docs: list[dict]) -> list[dict]:
    """R4: 单 CJK 字高频出现。"""
    counter = Counter()
    for doc in docs:
        for t in doc["tokens"]:
            if len(t) == 1 and "一" <= t <= "鿿":
                counter[t] += 1

    return [
        {"token": t, "frequency": f}
        for t, f in counter.most_common(100)
        if f >= 3
    ]


def r5_filler_pattern(keywords: list[dict], docs: list[dict]) -> list[dict]:
    """R5: 高频 + 包含语气词成分 → 口头禅/互动词。"""
    filler_chars = set("啊呢吧嘛哈呀哦唉哎嘿嘻呵啦喽哒嘞呗嘻")
    total_docs = len(docs)

    candidates = []
    for kw in keywords[:400]:
        word = kw["word"]
        if any(c in filler_chars for c in word):
            doc_count = sum(1 for doc in docs if word in doc["tokens"])
            doc_pct = doc_count / total_docs if total_docs > 0 else 0
            if doc_pct > 0.08 and kw["frequency"] >= 5:
                candidates.append({
                    "word": word, "frequency": kw["frequency"],
                    "tfidf_score": round(kw["tfidf_score"], 4),
                    "doc_pct": round(doc_pct, 3),
                })

    candidates.sort(key=lambda x: x["frequency"], reverse=True)
    return candidates


def r6_cross_topic_contamination(topics: list[dict]) -> list[dict]:
    """R6: 出现在 ≥4 个主题 Top-10 关键词中的词 → 主题污染源。"""
    word_topics = defaultdict(set)
    for topic in topics:
        for kw in topic["keywords"]:
            word_topics[kw["word"]].add(topic["topic_index"])

    candidates = []
    for word, topic_set in word_topics.items():
        if len(topic_set) >= 4:
            candidates.append({
                "word": word,
                "num_topics": len(topic_set),
                "topics": sorted(topic_set),
            })

    candidates.sort(key=lambda x: x["num_topics"], reverse=True)
    return candidates


# ---------------------------------------------------------------------------
# 综合噪声评分
# ---------------------------------------------------------------------------

def compute_noise_score(
    word: str,
    r1_cats: dict,
    r2_results: list[dict],
    r3_results: list[dict],
    r4_results: list[dict],
    r5_results: list[dict],
    r6_results: list[dict],
    existing_stopwords: set[str],
) -> float:
    """综合噪声评分 (0-100)。越高越可能是噪声。"""
    if word in existing_stopwords:
        return 0.0

    score = 0.0

    # R1 确定性噪声 → +100（必杀）
    for cat in ["whitespace", "punctuation", "symbol", "digit"]:
        tokens_in_cat = {i["token"] for i in r1_cats.get(cat, [])}
        if word in tokens_in_cat:
            return 100.0

    # R1 单字 → +80
    for cat in ["single_cjk", "single_ascii", "single_other"]:
        tokens_in_cat = {i["token"] for i in r1_cats.get(cat, [])}
        if word in tokens_in_cat:
            score += 80.0
            break

    # R2 高频低 TF-IDF → +50
    r2_words = {i["word"]: i["freq_tfidf_ratio"] for i in r2_results}
    if word in r2_words:
        score += min(50.0, r2_words[word] / 2)

    # R3 高主题熵 → +40
    r3_words = {i["word"]: i["normalized_entropy"] for i in r3_results}
    if word in r3_words:
        score += r3_words[word] * 40.0

    # R4 单字高频 → +60
    r4_words = {i["token"]: i["frequency"] for i in r4_results}
    if word in r4_words:
        score += min(60.0, r4_words[word])

    # R5 语气词 → +30
    r5_words = {i["word"]: i["doc_pct"] for i in r5_results}
    if word in r5_words:
        score += r5_words[word] * 200.0

    # R6 跨主题污染 → +45
    r6_words = {i["word"]: i["num_topics"] for i in r6_results}
    if word in r6_words:
        score += r6_words[word] * 10.0

    return round(min(100.0, score), 1)


def assemble_noise_list(
    docs: list[dict],
    keywords: list[dict],
    topics: list[dict],
    r1_cats: dict,
    r2_results: list[dict],
    r3_results: list[dict],
    r4_results: list[dict],
    r5_results: list[dict],
    r6_results: list[dict],
    existing_stopwords: set[str],
) -> list[dict]:
    """汇总所有候选词，计算噪声分数并排序。"""
    all_words = set()

    # 收集所有候选词
    for cat, items in r1_cats.items():
        for item in items:
            all_words.add(item["token"])
    for item in r2_results:
        all_words.add(item["word"])
    for item in r3_results:
        all_words.add(item["word"])
    for item in r4_results:
        all_words.add(item["token"])
    for item in r5_results:
        all_words.add(item["word"])
    for item in r6_results:
        all_words.add(item["word"])

    scored = []
    for word in all_words:
        s = compute_noise_score(
            word, r1_cats, r2_results, r3_results,
            r4_results, r5_results, r6_results, existing_stopwords,
        )
        if s > 0:
            # 获取词频
            freq = 0
            for kw in keywords:
                if kw["word"] == word:
                    freq = kw["frequency"]
                    break
            if freq == 0:
                for doc in docs:
                    freq += doc["tokens"].count(word)
            scored.append({"word": word, "noise_score": s, "frequency": freq})

    scored.sort(key=lambda x: x["noise_score"], reverse=True)
    return scored


# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------

def print_report(
    topics: list[dict],
    r1_cats: dict,
    noise_list: list[dict],
    new_stopwords: list[str],
):
    """打印结构化分析报告。"""
    sep = "=" * 68

    print("\n" + sep)
    print(" " * 18 + "NOISE WORD ANALYSIS REPORT")
    print(sep)

    # A. 主题质量评估
    print("\nA. TOPIC QUALITY ASSESSMENT (current)")
    print("-" * 50)
    coh_values = [t["coherence_score"] for t in topics]
    if coh_values:
        print(f"   Coherence range: {min(coh_values):.4f} ~ {max(coh_values):.4f}")
        print(f"   Mean coherence:  {sum(coh_values)/len(coh_values):.4f}")

    for t in topics:
        kws = t["keywords"]
        noise_count = sum(
            1 for k in kws
            if char_category(k["word"]) != "valid" or len(k["word"]) == 1
        )
        noise_pct = noise_count / len(kws) * 100 if kws else 0
        flag = " ⚠️" if noise_pct >= 20 else ""
        label_short = t["label"][:55] if t["label"] else "(no label)"
        print(f"   Topic {t['topic_index']:2d}: noise={noise_pct:5.1f}%  coh={t['coherence_score']:.4f}  [{label_short}]{flag}")

    # B. 噪声词 Top 100
    print(f"\nB. NOISE WORDS TOP 100 (total scored: {len(noise_list)})")
    print("-" * 50)

    # 按类别分组
    cats_display = {
        "whitespace": "Whitespace",
        "punctuation": "Punctuation",
        "symbol": "Symbols",
        "digit": "Digits",
        "single_cjk": "Single-char CJK",
        "single_ascii": "Single ASCII",
        "single_other": "Single Other",
    }

    for cat_key, cat_label in cats_display.items():
        items = r1_cats.get(cat_key, [])
        if items:
            words = " ".join(i["token"] for i in items[:15])
            print(f"\n   [{cat_label}] ({len(items)} total)")
            print(f"   {words}")

    # R2/R3/R5/R6 非确定性噪声
    top_noise = noise_list[:100]
    for cat_label, score_range in [
        ("High-confidence noise (score >= 80)", (80, 100)),
        ("Medium-confidence noise (score 40-79)", (40, 79)),
        ("Low-confidence noise (score 1-39)", (1, 39)),
    ]:
        group = [n for n in top_noise if score_range[0] <= n["noise_score"] <= score_range[1]]
        if group:
            print(f"\n   [{cat_label}] ({len(group)} words)")
            for i, n in enumerate(group[:20]):
                print(f"   {i+1:2d}. {n['word']:<20s} score={n['noise_score']:5.1f}  freq={n['frequency']:>4d}")

    # C. 推荐新增停用词
    print(f"\nC. RECOMMENDED NEW STOPWORDS (top {len(new_stopwords)})")
    print("-" * 50)
    for i, w in enumerate(new_stopwords[:100]):
        print(f"   {i+1:3d}. {w}")
    if len(new_stopwords) > 100:
        print(f"   ... and {len(new_stopwords) - 100} more")

    # D. 主题污染来源
    print(f"\nD. TOPIC CONTAMINATION SOURCES")
    print("-" * 50)
    for t in topics:
        kws = t["keywords"]
        noise_kws = [
            k for k in kws
            if char_category(k["word"]) != "valid" or len(k["word"]) == 1
        ]
        if noise_kws:
            noise_str = ", ".join(
                f'"{k["word"]}"(w={k["weight"]:.4f})' for k in noise_kws[:5]
            )
            print(f"   Topic {t['topic_index']:2d}: {noise_str}")

    # E. 修改方案
    print(f"\nE. MODIFICATION PLAN")
    print("-" * 50)
    print(f"   1. Fix cleaner.py: add _is_valid_token() filter in tokenize()")
    print(f"   2. Append {len(new_stopwords)} words to merged_stopwords.txt")
    print(f"   3. Run: python scripts/run_pipeline.py --force-reprocess --skip-bertopic")
    print(f"   4. Re-run this script to verify improvement")

    print("\n" + sep)


# ---------------------------------------------------------------------------
# save/load snapshot
# ---------------------------------------------------------------------------

def save_snapshot(topics: list[dict], noise_list: list[dict]):
    """保存当前主题状态快照。"""
    snap = {
        "timestamp": datetime.now().isoformat(),
        "topics": [
            {
                "topic_index": t["topic_index"],
                "label": t["label"],
                "coherence_score": t["coherence_score"],
                "keywords": [
                    {"word": k["word"], "weight": k["weight"], "rank": k["rank"]}
                    for k in t["keywords"]
                ],
            }
            for t in topics
        ],
        "noise_count": sum(
            1 for n in noise_list if n["noise_score"] >= 50
        ),
        "total_noise_scored": len(noise_list),
    }
    SNAPSHOT_PATH.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("快照已保存至 %s", SNAPSHOT_PATH)


def compare_snapshot():
    """对比修改前后的主题质量。"""
    if not SNAPSHOT_PATH.exists():
        logger.error("快照文件 %s 不存在。请先运行 --analyze 生成快照。", SNAPSHOT_PATH)
        return

    before = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))

    conn = get_engine().connect()
    after_topics = load_topics(conn)
    conn.close()

    print("\n" + "=" * 78)
    print(" " * 25 + "BEFORE vs AFTER COMPARISON")
    print("=" * 78)

    # Coherence 对比
    print(f"\n{'Topic':<8} {'Before Label':<30} {'Before Coh':>10} {'After Label':<30} {'After Coh':>10} {'ΔCoh':>8}")
    print("-" * 96)

    before_topics = {t["topic_index"]: t for t in before["topics"]}
    after_topics_map = {t["topic_index"]: t for t in after_topics}

    all_indices = sorted(set(list(before_topics.keys()) + list(after_topics_map.keys())))
    improvements = []
    for idx in all_indices:
        bt = before_topics.get(idx)
        at = after_topics_map.get(idx)
        b_label = bt["label"][:28] if bt else "N/A"
        b_coh = f"{bt['coherence_score']:.4f}" if bt else "N/A"
        a_label = at["label"][:28] if at else "N/A"
        a_coh = f"{at['coherence_score']:.4f}" if at else "N/A"

        delta = ""
        if bt and at:
            d = at["coherence_score"] - bt["coherence_score"]
            delta = f"{d:+.4f}"
            improvements.append(d)

        print(f"  {idx:<6d} {b_label:<30s} {b_coh:>10s} {a_label:<30s} {a_coh:>10s} {delta:>8s}")

    if improvements:
        avg_imp = sum(improvements) / len(improvements)
        print(f"\n  平均 coherence 变化: {avg_imp:+.4f}")
        pos = sum(1 for i in improvements if i > 0)
        print(f"  提升的主题: {pos}/{len(improvements)}")

    # 噪声检查
    print(f"\n{'Topic':<8} {'Before Noise KW':<40} {'After Noise KW'}")
    print("-" * 96)
    for idx in all_indices:
        bt = before_topics.get(idx)
        at = after_topics_map.get(idx)

        b_noise = []
        if bt:
            for k in bt["keywords"]:
                cat = char_category(k["word"])
                if cat != "valid" or len(k["word"]) == 1:
                    b_noise.append(k["word"])
        a_noise = []
        if at:
            for k in at["keywords"]:
                cat = char_category(k["word"])
                if cat != "valid" or len(k["word"]) == 1:
                    a_noise.append(k["word"])

        b_str = ", ".join(b_noise[:6]) if b_noise else "(clean)"
        a_str = ", ".join(a_noise[:6]) if a_noise else "✅ (clean)"
        print(f"  {idx:<6d} {b_str:<40s} {a_str}")

    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# --apply: 追加停用词 + 重跑 pipeline
# ---------------------------------------------------------------------------

def apply_stopwords(new_stopwords: list[str]):
    """追加推荐的停用词到 merged_stopwords.txt（去重）。"""
    existing = load_stopwords()
    to_add = [w for w in new_stopwords if w not in existing]

    if not to_add:
        logger.info("无新增停用词，所有候选已在文件中")
        return 0

    with open(STOPWORDS_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n# 自动识别 - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        for w in to_add:
            f.write(f"{w}\n")

    logger.info("已追加 %d 个停用词至 %s", len(to_add), STOPWORDS_PATH)
    return len(to_add)


def rerun_pipeline():
    """重新运行 NLP 流水线。"""
    import subprocess
    cmd = [
        sys.executable, str(_BACKEND_DIR / "scripts" / "run_pipeline.py"),
        "--force-reprocess", "--skip-bertopic",
    ]
    logger.info("执行: %s", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(_BACKEND_DIR))
    if result.returncode != 0:
        logger.error("Pipeline 退出码: %d", result.returncode)
        sys.exit(result.returncode)
    logger.info("Pipeline 完成")


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def run_analyze():
    """执行完整分析并输出报告。"""
    conn = get_engine().connect()
    logger.info("加载数据...")

    docs = load_comments(conn)
    keywords = load_keywords(conn)
    topics = load_topics(conn)
    existing_stopwords = load_stopwords()

    logger.info("文档数=%d, 关键词数=%d, 主题数=%d, 现有停用词=%d",
                 len(docs), len(keywords), len(topics), len(existing_stopwords))

    # 运行 6 条规则
    logger.info("R1: 字符类型过滤...")
    r1_cats = r1_character_type(docs)

    logger.info("R2: 高文档频率 + 低 TF-IDF...")
    r2_results = r2_high_doc_low_tfidf(keywords, docs)

    logger.info("R3: 主题均匀分布...")
    r3_results = r3_topic_entropy(docs, topics)

    logger.info("R4: 单字高频...")
    r4_results = r4_single_char_high_freq(docs)

    logger.info("R5: 语气词模式...")
    r5_results = r5_filler_pattern(keywords, docs)

    logger.info("R6: 跨主题污染...")
    r6_results = r6_cross_topic_contamination(topics)

    # 汇总噪声分数
    noise_list = assemble_noise_list(
        docs, keywords, topics,
        r1_cats, r2_results, r3_results, r4_results, r5_results, r6_results,
        existing_stopwords,
    )

    # 推荐新增停用词（score >= 30 且不在现有停用词中）
    new_stopwords = [
        n["word"] for n in noise_list
        if n["noise_score"] >= 30 and n["word"] not in existing_stopwords
    ]

    # 打印报告
    print_report(topics, r1_cats, noise_list, new_stopwords)

    # 保存快照
    save_snapshot(topics, noise_list)

    conn.close()
    return noise_list, new_stopwords


def main():
    parser = argparse.ArgumentParser(description="数据驱动噪声词分析工具")
    parser.add_argument("--apply", action="store_true",
                        help="分析 + 追加停用词 + 重跑 pipeline")
    parser.add_argument("--compare", action="store_true",
                        help="对比修改前后的主题质量")
    args = parser.parse_args()

    if args.compare:
        compare_snapshot()
        return

    noise_list, new_stopwords = run_analyze()

    if args.apply:
        if not new_stopwords:
            logger.warning("无推荐停用词，跳过追加")
            return
        n = apply_stopwords(new_stopwords)
        if n > 0:
            rerun_pipeline()
            # 重跑后再分析一次
            logger.info("重新分析修改后的数据...")
            run_analyze()


if __name__ == "__main__":
    main()
