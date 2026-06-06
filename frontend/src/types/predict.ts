/** 实时预测类型 */

export interface PredictResult {
  cleaned_text: string
  tokens: string[]
  snownlp_score: number
  sentiment_class: 'positive' | 'neutral' | 'negative'
  dominant_topic_label: string | null
  top_keywords: string[]
}

export interface BatchPredictItem {
  index: number
  text: string
  result: PredictResult
}

export interface BatchPredictResult {
  items: BatchPredictItem[]
  total: number
  avg_sentiment: number | null
}

// ── 梯度提升预测 ──

export interface GBPredictResult {
  sentiment_class: string
  probabilities: Record<string, number>
  model_used: string
}

export interface GBBatchPredictItem {
  index: number
  text: string
  sentiment_class: string
  probabilities: Record<string, number>
}

export interface GBBatchPredictResponse {
  items: GBBatchPredictItem[]
  total: number
}

export interface GBTrainResult {
  models: Record<string, unknown>
  has_trained: boolean
}

export interface GBModelInfo {
  name: string
  path: string
  is_best: boolean
}

export interface GBModelList {
  models: GBModelInfo[]
  has_trained: boolean
}
