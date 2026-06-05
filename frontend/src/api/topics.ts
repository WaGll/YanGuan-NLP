/** 主题分析 API 模块 */

import type { TopicItem, TopicDetail } from '@/types/topics'
import client from './client'

export async function getTopics(method: string = 'lda'): Promise<TopicItem[]> {
  const res = await client.get('/topics', {
    params: { method },
  })
  return res.data ?? []
}

/** 从已获取的 TopicItem 构建详情（无需额外 API 请求） */
export function getTopicDetail(topic: TopicItem): TopicDetail {
  return {
    topic,
    representative_comments: topic.representative_comments ?? [],
    keyword_count: topic.keywords?.length ?? 0,
  }
}
