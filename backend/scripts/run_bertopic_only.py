#!/usr/bin/env python3
"""单独运行 BERTopic 主题建模（跳过 LDA 和全量清洗）。"""

import asyncio
import logging
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.utils.resources import NLPResources
from app.services.topic import TopicService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("bertopic-runner")


async def main():
    # 加载 NLP 资源
    logger.info("加载 NLP 资源...")
    resources = NLPResources.get_instance()
    resources.load(settings.data_dir)

    # 创建数据库引擎
    db_url = settings.database_url
    if "aiosqlite" not in db_url:
        db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        topic_service = TopicService(session)
        k = await topic_service.run_bertopic()
        if k > 0:
            logger.info("BERTopic 成功: %d 个主题", k)

            # 输出主题摘要
            topics = await topic_service.get_topics("bertopic")
            print("\n" + "=" * 60)
            print("BERTopic 主题列表")
            print("=" * 60)
            for t in topics:
                bl = t.get("business_label") or t["label"]
                print(f"  [{t['topic_index']}] {bl}")
                print(f"       关键词: {', '.join(kw['word'] for kw in t['keywords'][:5])}")
                print(f"       文档数: {t['doc_count']}")
        else:
            logger.error("BERTopic 返回 0 个主题")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
