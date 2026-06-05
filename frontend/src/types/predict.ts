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
