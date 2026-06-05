import client from './client'
import type {
  EmoteDistributionData,
  EmoteDetail,
  EmoteSentimentCorrelation,
  EmoteTimelinePoint,
} from '@/types/emotes'

/**
 * 获取表情频率分布及情感统计
 */
export async function fetchEmoteDistribution(
  sortBy: string = 'frequency',
  limit: number = 50,
  sentiment?: string
): Promise<EmoteDistributionData> {
  const res = await client.get('/emotes', {
    params: { sort_by: sortBy, limit, sentiment: sentiment || 'all' },
  })
  return (res as any).data ?? { emotes: [], sentiment_breakdown: { positive: 0, negative: 0, neutral: 0, total: 0, positive_pct: 0, negative_pct: 0, neutral_pct: 0 }, total_distinct_emotes: 0, total_emote_occurrences: 0 }
}

/**
 * 获取表情-文本情感相关性分析
 */
export async function fetchEmoteSentimentCorrelation(): Promise<EmoteSentimentCorrelation[]> {
  const res = await client.get('/emotes/sentiment')
  return (res as any).data ?? []
}

/**
 * 获取单个表情详情
 */
export async function fetchEmoteDetail(name: string): Promise<EmoteDetail | null> {
  const res = await client.get(`/emotes/${encodeURIComponent(name)}`)
  return (res as any).data ?? null
}

/**
 * 获取表情词云数据
 */
export async function fetchEmoteWordcloud(limit: number = 100): Promise<{ name: string; value: number }[]> {
  const res = await client.get('/emotes/wordcloud', { params: { limit } })
  return (res as any).data ?? []
}

/**
 * 获取指定表情的时间趋势
 */
export async function fetchEmoteTimeline(
  name: string,
  granularity: string = 'month'
): Promise<EmoteTimelinePoint[]> {
  const res = await client.get(`/emotes/${encodeURIComponent(name)}/timeline`, {
    params: { granularity },
  })
  return (res as any).data ?? []
}
