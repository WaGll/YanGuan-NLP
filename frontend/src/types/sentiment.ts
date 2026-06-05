/** 情感分析类型 */

export interface SentimentBin {
  label: string
  count: number
  percentage: number
}

export interface SentimentDistribution {
  bins: SentimentBin[]
  total: number
}

export interface MLScore {
  model_name: string
  cv_mean: number
  cv_std: number
  best_params: Record<string, unknown> | null
}
