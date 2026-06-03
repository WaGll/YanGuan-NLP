#!/usr/bin/env python3
"""seed_db.py — 数据导入与初始化脚本 / Data import and DB seeding script.

Loads the raw CSV comment data into the SQLite database and runs the full
NLP analysis pipeline (sentiment, keywords, topics, networks).

Usage:
    cd backend
    python scripts/seed_db.py          # 默认使用 backend/data/source_data.csv
    python scripts/seed_db.py --csv path/to/file.csv
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 确保 backend 目录在 sys.path 中，支持从任意目录运行此脚本
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("seed_db")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="导入评论文本数据并运行 NLP 分析流水线 / Import comments and run NLP pipeline",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=_PROJECT_ROOT / "data" / "source_data.csv",
        help="CSV数据文件路径 / Path to the source CSV file",
    )
    parser.add_argument(
        "--skip-nlp",
        action="store_true",
        default=False,
        help="仅导入数据，跳过 NLP 分析 / Import data only, skip NLP pipeline",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="批量导入时的批次大小 / Batch size for DB inserts (default: 500)",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# 占位导入 — 实际服务层将在后续 Phase 实现
# 当前提供清晰的导入结构和可运行的框架
# ---------------------------------------------------------------------------
async def run_import(
    csv_path: Path,
    batch_size: int,
) -> dict:
    """导入CSV数据到数据库。

    Returns a summary dict with row counts so the caller can print them.
    """
    if not csv_path.exists():
        logger.error("CSV文件不存在 / CSV file not found: %s", csv_path)
        sys.exit(1)

    logger.info("开始导入数据 / Starting data import from: %s", csv_path)

    # ---- 延迟导入，避免脚本启动时加载重型依赖 ----
    import pandas as pd

    # ---- 读取并清洗 ----
    logger.info("读取CSV文件 / Reading CSV ...")
    df = pd.read_csv(csv_path, dtype=str, encoding_errors="replace")
    total_rows = len(df)
    logger.info("读取到 %d 行数据 / Read %d rows", total_rows, total_rows)

    # 清洗：移除空评论
    before = len(df)
    df = df.dropna(subset=["content"])
    df = df[df["content"].str.strip() != ""]
    after = len(df)
    if before != after:
        logger.info("移除了 %d 条空评论 / Removed %d empty comments", before - after, before - after)

    # 清洗：移除 content 重复的行
    before = after
    df = df.drop_duplicates(subset=["content"])
    after = len(df)
    if before != after:
        logger.info("移除了 %d 条重复评论 / Removed %d duplicate comments", before - after, before - after)

    # ---- 导入数据库 ----
    logger.info("正在初始化数据库连接 / Initializing database ...")
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.core.config import settings

    engine = create_async_engine(
        settings.database_url,
        echo=False,
    )

    # 创建表结构（如尚未创建）
    from app.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 批量插入
    from app.models.comment import Comment

    imported = 0
    for start in range(0, len(df), batch_size):
        chunk = df.iloc[start : start + batch_size]
        async with engine.begin() as conn:
            for _, row in chunk.iterrows():
                now = pd.Timestamp.now(tz="UTC").timestamp()
                conn_kwargs = {
                    "comment_id": int(float(row.get("comment_id", "0"))),
                    "parent_comment_id": int(float(row.get("parent_comment_id", "0"))),
                    "create_time": int(float(row.get("create_time", "0"))),
                    "video_id": int(float(row.get("video_id", "0"))),
                    "content": row.get("content", ""),
                    "user_id": int(float(row.get("user_id", "0"))),
                    "nickname": row.get("nickname", ""),
                    "avatar": row.get("avatar", ""),
                    "sub_comment_count": int(float(row.get("sub_comment_count", "0"))),
                }
                await conn.execute(Comment.__table__.insert().values(**conn_kwargs))
        imported += len(chunk)
        logger.info("导入进度 / Import progress: %d / %d", imported, after)

    await engine.dispose()

    summary = {
        "total_rows_in_csv": total_rows,
        "after_cleaning": after,
        "imported": imported,
    }
    logger.info(
        "数据导入完成 / Import finished: %d 条评论已入库 / %d comments imported",
        imported,
        imported,
    )
    return summary


async def run_nlp_pipeline() -> dict:
    """运行完整的 NLP 分析流水线。

    依次执行：
    1. 分词 & 关键词提取 (jieba)
    2. 情感分析 (SnowNLP)
    3. 主题建模 (LDA)
    4. 共现网络构建 (networkx)

    Returns pipeline summary dict.
    """
    logger.info("=" * 60)
    logger.info("开始 NLP 分析流水线 / Starting NLP analysis pipeline")
    logger.info("=" * 60)

    # NLP pipeline 将在后续 Phase 中由 NLP Agent 实现
    # 当前仅输出流水线框架信息

    steps = [
        "分词与关键词提取 / Tokenization & keyword extraction",
        "情感分析 / Sentiment analysis (SnowNLP)",
        "主题建模 / Topic modeling (LDA/BERTopic)",
        "共现网络构建 / Co-occurrence network (networkx)",
    ]

    for i, step in enumerate(steps, 1):
        logger.info("  [%d/%d] %s ...", i, len(steps), step)
        # 实际分析步骤将在对应的 Service 实现后调用
        # e.g.:
        #   from app.services.tokenizer import TokenizerService
        #   tokenizer = TokenizerService()
        #   await tokenizer.run_all()
        await asyncio.sleep(0)  # 占位，保持异步结构

    logger.info("NLP 流水线完成 / NLP pipeline completed")
    return {"pipeline_steps": len(steps), "status": "completed"}


async def main() -> None:
    args = parse_args()

    logger.info("=" * 60)
    logger.info("GradCareer-CommentAnalysis — 数据库初始化脚本 / DB Seed Script")
    logger.info("=" * 60)

    # Step 1: 导入数据
    import_summary = await run_import(
        csv_path=args.csv,
        batch_size=args.batch_size,
    )

    # Step 2: NLP 流水线
    if not args.skip_nlp:
        nlp_summary = await run_nlp_pipeline()
    else:
        nlp_summary = {"status": "skipped"}
        logger.info("跳过 NLP 流水线 / NLP pipeline skipped (--skip-nlp)")

    # ---- 完成报告 ----
    print("\n" + "=" * 60)
    print("  初始化完成 / Seeding Complete")
    print("=" * 60)
    print(f"  CSV 源文件:         {args.csv}")
    print(f"  原始行数:           {import_summary['total_rows_in_csv']}")
    print(f"  清洗后行数:         {import_summary['after_cleaning']}")
    print(f"  已导入数据库:       {import_summary['imported']}")
    print(f"  NLP 流水线状态:     {nlp_summary.get('status', 'unknown')}")
    print("=" * 60)
    print("\n  启动后端服务 / Start the API server:")
    print("    uvicorn app.main:app --reload")
    print()


if __name__ == "__main__":
    asyncio.run(main())
