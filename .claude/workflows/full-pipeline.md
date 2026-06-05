# Workflow: 全管道执行

## 描述

从零开始执行完整的数据处理和分析管道。适用于首次初始化或完全重做分析。

## 触发条件

- 用户说"重跑全管道"、"重新开始分析"
- 数据库损坏需要重建
- 数据更新后需要重新分析

## 工作流步骤

### Phase 1: 验证环境

Agent: Backend Agent

```bash
# 1.1 检查 Python 版本
python --version  # 要求 ≥3.12

# 1.2 检查依赖
cd backend && python -c "
import fastapi; import sqlalchemy; import jieba
import snownlp; import sklearn; import gensim; import networkx
print('所有依赖已安装')
"

# 1.3 检查数据文件
ls -la backend/data/毕业去向讨论.csv
ls -la backend/data/merged_stopwords.txt
ls -la backend/data/自定义字典.txt
ls -la backend/data/同义词.txt
```

### Phase 2: 数据库初始化

Agent: Backend Agent

```bash
# 2.1 删除旧数据库（如需重建）
rm -f backend/yanguan.db backend/yanguan.db-wal backend/yanguan.db-shm

# 2.2 初始化表结构
cd backend && python -c "
import asyncio
from app.database import init_db

async def main():
    await init_db()
    print('数据库表已创建')

asyncio.run(main())
"
```

### Phase 3: 数据导入

Agent: Backend Agent

```bash
# 3.1 导入 CSV 数据
cd backend && python -c "
import asyncio
from app.database import async_session_factory, init_db
from app.services.data_loader import DataLoaderService

async def main():
    await init_db()
    async with async_session_factory() as db:
        loader = DataLoaderService(db)
        count = await loader.load_csv('data/毕业去向讨论.csv')
        print(f'导入 {count} 条评论')

asyncio.run(main())
"
```

### Phase 4: 文本清洗

Agent: NLP Agent

```bash
cd backend && python -c "
import asyncio
from pathlib import Path
from app.database import async_session_factory, init_db
from app.services.cleaner import CleanerService
from app.utils.resources import NLPResources

async def main():
    await init_db()
    NLPResources.get_instance().load(Path('data'))
    async with async_session_factory() as db:
        cleaner = CleanerService(db)
        count = await cleaner.process_all(batch_size=500)
        print(f'清洗完成: {count} 条')

asyncio.run(main())
"
```

### Phase 5: 情感分析

Agent: NLP Agent

```bash
cd backend && python -c "
import asyncio
from app.database import async_session_factory, init_db
from app.services.sentiment import SentimentService

async def main():
    await init_db()
    async with async_session_factory() as db:
        service = SentimentService(db)
        result = await service.analyze_all()
        print(f'情感分析完成: {result}')

asyncio.run(main())
"
```

### Phase 6: 关键词 + 主题 + 网络

Agent: NLP Agent

```bash
cd backend && python -c "
import asyncio
from pathlib import Path
from app.database import async_session_factory, init_db
from app.services.keyword import KeywordService
from app.services.topic import TopicService
from app.services.network import NetworkService
from app.utils.resources import NLPResources

async def main():
    await init_db()
    NLPResources.get_instance().load(Path('data'))
    async with async_session_factory() as db:
        # 关键词
        kw = KeywordService(db)
        await kw.extract_all()
        print('关键词提取完成')

        # 主题建模
        topic = TopicService(db)
        await topic.train_lda(n_topics=5, passes=20)
        print('主题建模完成')

        # 语义网络
        net = NetworkService(db)
        result = await net.build_cooccurrence_graph(top_k=100)
        print(f'语义网络: {len(result[\"nodes\"])} 节点, {len(result[\"edges\"])} 边')

asyncio.run(main())
"
```

### Phase 7: 验证结果

Agent: QA Agent

```bash
# 启动后端验证
cd backend && uvicorn app.main:app &
sleep 3

# 健康检查
curl http://localhost:3001/api/health

# 仪表盘数据
curl http://localhost:3001/api/dashboard | python -m json.tool

# 情感分析
curl http://localhost:3001/api/sentiment | python -m json.tool

# 预测测试
curl -X POST http://localhost:3001/api/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "数学太难了，但是统计学很有意思"}'
```

### Phase 8: 运行测试

Agent: QA Agent

```bash
cd backend && pytest tests/ -v --cov=app
```

## 预计总耗时

- 总计: ~5 分钟
- 数据导入: ~30 秒
- 文本清洗: ~1 分钟
- 情感分析: ~30 秒
- 关键词: ~10 秒
- LDA 主题建模: ~2 分钟
- 语义网络: ~30 秒
- 验证: ~10 秒
