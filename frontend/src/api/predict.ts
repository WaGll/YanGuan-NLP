import client from './client'
import type {
  GBPredictResult,
  GBBatchPredictResponse,
  GBTrainResult,
  GBModelList,
} from '@/types/predict'

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

// ── 梯度提升预测 ──

/**
 * 梯度提升单条情感预测
 */
export async function predictGB(
  text: string,
  model: string = 'best'
): Promise<GBPredictResult> {
  const res = await client.post('/predict/gb', { text }, { params: { model } })
  return res.data
}

/**
 * 梯度提升批量情感预测
 */
export async function predictGBBatch(
  texts: string[],
  model: string = 'best'
): Promise<GBBatchPredictResponse> {
  const res = await client.post('/predict/gb/batch', { texts }, { params: { model } })
  return res.data
}

/**
 * 训练梯度提升模型
 */
export async function trainGB(): Promise<GBTrainResult> {
  const res = await client.post('/predict/gb/train')
  return res.data
}

/**
 * 列出已训练的梯度提升模型
 */
export async function listGBModels(): Promise<GBModelList> {
  const res = await client.get('/predict/gb/models')
  return res.data
}
