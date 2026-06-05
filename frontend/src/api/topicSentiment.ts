/** 主题×情感联合分析 API 模块 */

import client from './client'
import type { TopicSentimentData } from '@/types/topic-sentiment'

export async function getTopicSentimentMatrix(
  method: string = 'lda'
): Promise<TopicSentimentData> {
  const res = await client.get('/topic-sentiment', {
    params: { method },
  })
  return (
    res.data ?? {
      topics: [],
      sentiment_classes: [],
      cells: [],
    }
  )
}
