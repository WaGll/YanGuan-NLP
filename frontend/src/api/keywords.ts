import client from './client'

export interface KeywordItem {
  word: string
  frequency: number
}

export interface WordcloudItem {
  name: string
  value: number
}

/**
 * 获取关键词列表
 */
export async function fetchKeywords(
  sortBy: 'frequency' | 'word' = 'frequency',
  limit: number = 50
): Promise<KeywordItem[]> {
  const res = await client.get('/keywords', {
    params: { sort_by: sortBy, limit },
  })
  return res.data.keywords ?? []
}

/**
 * 获取词云数据
 */
export async function fetchWordcloudData(): Promise<WordcloudItem[]> {
  const res = await client.get('/keywords', {
    params: { sort_by: 'frequency', limit: 200 },
  })
  return res.data.wordcloud_data ?? []
}
