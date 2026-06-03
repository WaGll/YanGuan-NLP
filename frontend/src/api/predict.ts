import client from './client'

export interface PredictResult {
  sentiment_class: 'positive' | 'negative' | 'neutral'
  snownlp_score: number
  top_keywords: string[]
}

export interface BatchPredictItem {
  text: string
  result: PredictResult
}

/**
 * 单条评论实时情感预测
 */
export async function predictComment(text: string): Promise<PredictResult> {
  const res = await client.post('/predict', { text })
  return res.data
}

/**
 * 批量评论情感预测
 */
export async function predictBatch(texts: string[]): Promise<BatchPredictItem[]> {
  const res = await client.post('/predict/batch', { texts })
  return res.data
}
