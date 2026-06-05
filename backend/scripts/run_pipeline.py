#!/usr/bin/env python3
"""
YanGuan-NLP 数据处理流水线

按序执行完整 NLP 分析:
  DataLoader → Cleaner → Keyword(frequencies → TF-IDF)
  → Topic(LDA) → Topic(BERTopic) → Network → Sentiment

用法:
  python scripts/run_pipeline.py                      # 仅运行新数据
  python scripts/run_pipeline.py --force-reprocess    # 强制重新清洗全量数据
  python scripts/run_pipeline.py --skip-bertopic       # 跳过 BERTopic（加速）
  python scripts/run_pipeline.py --csv data/xxx.csv    # 指定 CSV 文件
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# 将 backend/ 加入 sys.path，确保从项目外也可运行
_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.utils.resources import NLPResources

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("pipeline")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="YanGuan-NLP 数据处理流水线")
    parser.add_argument(
        "--force-reprocess",
        action="store_true",
        help="强制重新清洗所有评论（清除已有 cleaned_content）",
    )
    parser.add_argument(
        "--skip-bertopic",
        action="store_true",
        help="跳过 BERTopic 主题建模",
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=None,
        help="CSV 文件路径（默认使用 data/source_data.csv）",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="批处理大小 (默认 500)",
    )
    parser.add_argument(
        "--progress",
        action="store_true",
        default=False,
        help="显示 tqdm 进度条（默认仅日志）",
    )
    return parser.parse_args()


def get_engine():
    """创建异步数据库引擎。"""
    db_url = settings.database_url
    if "aiosqlite" not in db_url:
        db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
    return create_async_engine(db_url, echo=False)


async def reset_clean_state(session: AsyncSession) -> int:
    """清除已有清洗结果，强制重新清洗。"""
    result = await session.execute(
        text("UPDATE comments SET cleaned_content = NULL, tokens_json = NULL, "
             "bigram_tokens_json = NULL, token_count = NULL")
    )
    await session.commit()
    count = result.rowcount
    logger.info("已清除 %d 条评论的清洗状态", count)
    return count


async def print_business_report(session: AsyncSession) -> None:
    """打印业务洞察报告（步骤 11）。

    聚合所有 NLP 分析结果，输出结构化业务解读。
    """
    from app.services.emote import EmoteService
    from app.services.keyword import KeywordService
    from app.services.sentiment import SentimentService
    from app.services.topic import TopicService
    from app.services.topic_sentiment import TopicSentimentService

    sent_svc = SentimentService(session)
    topic_svc = TopicService(session)
    kw_svc = KeywordService(session)
    emote_svc = EmoteService(session)
    ts_svc = TopicSentimentService(session)

    dist = await sent_svc.get_distribution()
    topics = await topic_svc.get_topics("lda")
    matrix = await ts_svc.compute_joint_matrix("lda")
    keywords = await kw_svc.get_keywords(sort_by="tfidf", limit=15)
    emotes = await emote_svc.get_sentiment_correlation()

    print("\n" + "=" * 70)
    print(" " * 22 + "BUSINESS INSIGHTS REPORT")
    print("=" * 70)

    # 1. 整体情感
    print("\n1. OVERALL SENTIMENT")
    for item in dist:
        bar = "█" * int(item["percentage"] / 2)
        print(f"   {item['label']:>8}: {item['percentage']:5.1f}% ({item['count']:,} comments)  {bar}")
    pos = next((d["percentage"] for d in dist if d["label"] == "positive"), 0)
    neg = next((d["percentage"] for d in dist if d["label"] == "negative"), 0)
    verdict = "positive 😊" if pos > neg else "negative 😞" if neg > pos else "balanced 😐"
    print(f"   >> Overall tone: {verdict}")

    # 2. 主要主题
    print("\n2. MAIN TOPICS (LDA)")
    for t in topics[:8]:
        coh = f" (coh={t['coherence_score']:.3f})" if t.get("coherence_score") else ""
        bl = t.get("business_label") or ""
        print(f"   [{t['topic_index']}] {bl:<12s} | {t['label']:.<32s} {t['doc_count']:>4} docs{coh}")

    # 3. 主题×情感极端值
    print("\n3. TOPIC × SENTIMENT EXTREMES")
    if matrix.get("cells"):
        pos_topic = neg_topic = None
        best_pos = best_neg = 0.0
        for row in matrix["cells"]:
            for cell in row:
                if cell["sentiment"] == "positive" and cell["proportion"] > best_pos:
                    best_pos = cell["proportion"]; pos_topic = cell
                if cell["sentiment"] == "negative" and cell["proportion"] > best_neg:
                    best_neg = cell["proportion"]; neg_topic = cell
        if pos_topic:
            print(f"   Most POSITIVE: {pos_topic['topic']} ({pos_topic['proportion']*100:.1f}%)")
        if neg_topic:
            print(f"   Most NEGATIVE: {neg_topic['topic']} ({neg_topic['proportion']*100:.1f}%)")

    # 4. Top 关键词
    print("\n4. TOP KEYWORDS (by TF-IDF)")
    for i, kw in enumerate(keywords[:10], 1):
        print(f"   {i:2}. {kw['word']:<20s}  freq={kw['frequency']:>5}  tfidf={kw['tfidf_score']:.3f}")

    # 5. 表情×情感
    print("\n5. EMOTE × SENTIMENT CORRELATION (top 10)")
    for c in emotes[:10]:
        print(f"   [{c['emote_name']:<16s}] label={c['emote_sentiment']:<8s}  "
              f"avg_text={c['avg_text_sentiment']:.3f}  delta={c['sentiment_delta']:+.3f}  n={c['comment_count']}")

    print("=" * 70)


async def run_pipeline(args: argparse.Namespace) -> None:
    """执行完整 NLP 流水线。"""
    engine = get_engine()
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    p = args.progress  # 进度条开关

    # 0. 加载 NLP 资源
    logger.info("=" * 60)
    logger.info("步骤 0: 加载 NLP 资源（jieba 词典 + 停用词 + 同义词）")
    resources = NLPResources.get_instance()
    resources.load(settings.data_dir)
    logger.info("停用词数量: %d", len(resources.stopwords))

    async with async_session() as session:
        # 0.5 数据库迁移：确保所有表存在
        logger.info("=" * 60)
        logger.info("步骤 0.5: 数据库迁移检查")
        from app.database import init_db
        await init_db()
        from sqlalchemy import text as sql_text
        try:
            await session.execute(
                sql_text("ALTER TABLE topics ADD COLUMN business_label VARCHAR(128)")
            )
            await session.commit()
            logger.info("已添加 topics.business_label 列")
        except Exception:
            logger.info("business_label 列已存在，跳过迁移")
        # Topic 模型新增的 LLM 相关列
        for col_name, col_type in [
            ("business_label_llm", "VARCHAR(128)"),
            ("business_label_confidence", "FLOAT"),
            ("needs_review", "BOOLEAN DEFAULT 0"),
        ]:
            try:
                await session.execute(
                    sql_text(f"ALTER TABLE topics ADD COLUMN {col_name} {col_type}")
                )
                await session.commit()
                logger.info("已添加 topics.%s 列", col_name)
            except Exception:
                logger.info("topics.%s 列已存在，跳过迁移", col_name)

        # 1. 数据导入
        logger.info("=" * 60)
        logger.info("步骤 1: 数据导入")
        from app.services.data_loader import DataLoaderService

        loader = DataLoaderService(session)
        csv_path = args.csv or str(settings.data_dir / "source_data.csv")
        csv_path = Path(csv_path)
        if not csv_path.exists():
            alt_csv = settings.data_dir / "毕业去向讨论.csv"
            if alt_csv.exists():
                csv_path = alt_csv

        if csv_path.exists():
            result = await loader.import_csv(csv_path)
            logger.info("CSV 导入完成: %s", result)
        else:
            logger.warning("未找到 CSV 文件，跳过数据导入")

        # 1.5 强制重新清洗
        if args.force_reprocess:
            logger.info("=" * 60)
            logger.info("步骤 1.5: 强制重新清洗（清除旧状态）")
            await reset_clean_state(session)

        # 2. 文本清洗 + 分词
        logger.info("=" * 60)
        logger.info("步骤 2: 文本清洗 + 分词")
        from app.services.cleaner import CleanerService

        cleaner = CleanerService(session)
        cleaned_count = await cleaner.process_all(batch_size=args.batch_size, progress=p)
        logger.info("清洗完成: %d 条评论", cleaned_count)

        # 2.5 短文本聚合（video + time window）
        if settings.aggregation_enabled:
            logger.info("=" * 60)
            logger.info("步骤 2.5: 短文本聚合（video + time window）")
            from app.services.aggregation import AggregationService

            agg_service = AggregationService(session)
            agg_count = await agg_service.process(
                window_minutes=settings.aggregation_window_minutes,
                min_comments=settings.aggregation_min_comments,
            )
            logger.info("聚合完成: %d 组", agg_count)
            topic_source = "comment_group"
        else:
            logger.info("跳过短文本聚合（aggregation_enabled=False）")
            topic_source = "comment"

        # 3-4. 关键词提取
        logger.info("=" * 60)
        logger.info("步骤 3: 关键词词频统计")
        from app.services.keyword import KeywordService

        kw_service = KeywordService(session)
        kw_count = await kw_service.compute_frequencies(progress=p)
        logger.info("词频统计完成: %d 个关键词", kw_count)

        logger.info("步骤 4: TF-IDF 计算")
        tfidf_results = await kw_service.compute_tfidf()
        logger.info("TF-IDF 完成: %d 个词", len(tfidf_results))

        # 5. LDA 主题建模
        logger.info("=" * 60)
        logger.info("步骤 5: LDA 主题建模（source=%s）", topic_source)
        from app.services.topic import TopicService

        topic_service = TopicService(session)
        lda_k = await topic_service.run_lda(source=topic_source)
        logger.info("LDA 完成: k=%d", lda_k)

        # 6. BERTopic 主题建模
        if not args.skip_bertopic:
            logger.info("=" * 60)
            logger.info("步骤 6: BERTopic 主题建模（source=%s）", topic_source)
            bertopic_k = await topic_service.run_bertopic(source=topic_source)
            logger.info("BERTopic 完成: k=%d", bertopic_k)
        else:
            logger.info("跳过 BERTopic（--skip-bertopic）")

        # 7. 共现网络
        logger.info("=" * 60)
        logger.info("步骤 7: 语义网络构建")
        from app.services.network import NetworkService

        net_service = NetworkService(session)
        net_result = await net_service.build_cooccurrence_graph()
        logger.info("网络构建完成: %s", net_result)

        # 8. 情感分析
        logger.info("=" * 60)
        logger.info("步骤 8: 情感分析")
        from app.services.sentiment import SentimentService

        sent_service = SentimentService(session)
        sent_count = await sent_service.compute_all(batch_size=args.batch_size, progress=p)
        logger.info("情感分析完成: %d 条", sent_count)

        # 阈值校准
        from app.models.sentiment import SentimentResult as SR
        from app.services.sentiment import NEGATIVE_THRESHOLD, POSITIVE_THRESHOLD

        scores_result = await session.execute(select(SR.snownlp_score))
        scores = [r[0] for r in scores_result.all() if r[0] is not None]
        cal = SentimentService.calibrate_thresholds(scores)
        logger.info("阈值校准: 建议 negative=%.3f positive=%.3f (当前=%.3f/%.3f) mean=%.3f n=%d",
                     cal["negative_threshold"], cal["positive_threshold"],
                     NEGATIVE_THRESHOLD, POSITIVE_THRESHOLD,
                     cal["mean"], cal["n"])

        # 9. 主题×情感
        logger.info("=" * 60)
        logger.info("步骤 9: 主题×情感联合分析")
        from app.services.topic_sentiment import TopicSentimentService

        ts_service = TopicSentimentService(session)
        ts_result = await ts_service.compute_joint_matrix("lda")
        logger.info("主题×情感完成: %s", ts_result)

        # 10. 趋势分析
        logger.info("=" * 60)
        logger.info("步骤 10: 趋势分析")
        from app.services.trend import TrendService

        trend_service = TrendService(session)
        trend_result = await trend_service.compute_sentiment_trend()
        logger.info("趋势分析完成: %s", trend_result)

        # 11. 业务洞察报告
        await print_business_report(session)

    await engine.dispose()
    logger.info("=" * 60)
    logger.info("流水线全部完成!")


def main():
    args = parse_args()
    asyncio.run(run_pipeline(args))


if __name__ == "__main__":
    main()
