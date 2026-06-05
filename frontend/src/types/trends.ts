/** 趋势分析类型 */

export interface TrendBucket {
  bucket_start: string
  bucket_end: string
  avg_sentiment: number | null
  comment_count: number
  positive_count: number
  neutral_count: number
  negative_count: number
}

export interface TrendData {
  series_type: string
  granularity: string
  buckets: TrendBucket[]
  total_points: number
}
