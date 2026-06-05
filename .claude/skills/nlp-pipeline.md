# Skill: nlp-pipeline

## 描述

运行或重跑特定的 NLP 分析流水线步骤。适用于数据已导入但需要重新分析、
或对特定分析模块进行调试。

## 触发条件

- 用户说"运行 NLP 管道"、"重新分析"、"跑一遍分析"
- 需要重新生成某个分析结果
- 调试 NLP 算法

## 可用操作

### 操作 1: 仅清洗文本

```bash
cd backend && python -c "
import asyncio
from app.database import async_session_factory, init_db
from app.services.cleaner import CleanerService
from app.utils.resources import NLPResources
from app.config import settings

async def run():
    await init_db()
    NLPResources.get_instance().load(settings.data_dir)
    async with async_session_factory() as db:
        service = CleanerService(db)
        count = await service.process_all(batch_size=500)
        print(f'Processed {count} comments')

asyncio.run(run())
"
```

### 操作 2: 仅情感分析

```bash
cd backend && python -c "
import asyncio
from app.database import async_session_factory, init_db
from app.services.sentiment import SentimentService

async def run():
    await init_db()
    async with async_session_factory() as db:
        service = SentimentService(db)
        result = await service.analyze_all()
        print(f'Sentiment analysis complete: {result}')

asyncio.run(run())
"
```

### 操作 3: 仅主题建模

```bash
cd backend && python -c "
import asyncio
from app.database import async_session_factory, init_db
from app.services.topic import TopicService

async def run():
    await init_db()
    async with async_session_factory() as db:
        service = TopicService(db)
        topics = await service.train_lda(n_topics=5, passes=20)
        print(f'Trained {len(topics)} topics')

asyncio.run(run())
"
```

### 操作 4: 仅语义网络

```bash
cd backend && python -c "
import asyncio
from app.database import async_session_factory, init_db
from app.services.network import NetworkService

async def run():
    await init_db()
    async with async_session_factory() as db:
        service = NetworkService(db)
        result = await service.build_cooccurrence_graph(top_k=100, window=2)
        print(f'Network: {len(result[\"nodes\"])} nodes, {len(result[\"edges\"])} edges')

asyncio.run(run())
"
```

### 操作 5: 运行全管道（使用 API）

```bash
# 通过 API 触发管道（如果实现了管道触发端点）
curl -X POST http://localhost:3001/api/pipeline/run
```

## 调试技巧

### 查看中间结果
```bash
cd backend && python -c "
import asyncio
from sqlalchemy import select, func
from app.database import async_session_factory, init_db
from app.models.comment import Comment

async def check():
    await init_db()
    async with async_session_factory() as db:
        # 查看清洗进度
        total = await db.scalar(select(func.count(Comment.id)))
        cleaned = await db.scalar(
            select(func.count(Comment.id)).where(Comment.cleaned_content.isnot(None))
        )
        print(f'Total: {total}, Cleaned: {cleaned}')

asyncio.run(check())
"
```

### 重置分析结果
```bash
cd backend && python -c "
import asyncio
from sqlalchemy import update
from app.database import async_session_factory, init_db
from app.models.comment import Comment
from app.models.keyword import Keyword
from app.models.sentiment import SentimentResult

async def reset():
    await init_db()
    async with async_session_factory() as db:
        # 清空评论的分析字段
        await db.execute(
            update(Comment).values(
                cleaned_content=None,
                tokens_json=None,
                bigram_tokens_json=None,
                token_count=None
            )
        )
        # 删除关键词、情感、主题、网络分析结果
        from sqlalchemy import delete
        from app.models.keyword import Keyword
        from app.models.sentiment import SentimentResult, SentimentMLScore
        from app.models.topic import Topic, TopicKeyword, DocTopic
        from app.models.network import NetworkNode, NetworkEdge
        from app.models.pipeline import PipelineRun

        for model in [Keyword, SentimentResult, SentimentMLScore,
                       Topic, TopicKeyword, DocTopic,
                       NetworkNode, NetworkEdge, PipelineRun]:
            await db.execute(delete(model))
        await db.commit()
        print('All analysis results reset')

asyncio.run(reset())
"
```
