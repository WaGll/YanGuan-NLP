import client from './client'

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
  best_params: Record<string, unknown>
}

export async function fetchSentiment(): Promise<SentimentDistribution> {
  const res = await client.get('/sentiment')
  return res.data
}

export async function fetchMLScores(): Promise<MLScore[]> {
  const res = await client.get('/sentiment/ml-scores')
  return res.data
}
