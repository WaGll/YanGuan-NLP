/** 表情分析类型 */

export interface EmoteItem {
  name: string
  frequency: number
  comment_count: number
  sentiment: 'positive' | 'negative' | 'neutral'
  percentage: number
}

export interface EmoteSentimentBreakdown {
  positive: number
  negative: number
  neutral: number
  total: number
  positive_pct: number
  negative_pct: number
  neutral_pct: number
}

export interface EmoteDistributionData {
  emotes: EmoteItem[]
  sentiment_breakdown: EmoteSentimentBreakdown
  total_distinct_emotes: number
  total_emote_occurrences: number
}

export interface EmoteDetail {
  name: string
  frequency: number
  comment_count: number
  sentiment: string
  sample_comments: string[]
  avg_text_sentiment: number | null
}

export interface EmoteSentimentCorrelation {
  emote_name: string
  emote_sentiment: string
  avg_text_sentiment: number
  comment_count: number
  sentiment_delta: number
}

export interface EmoteTimelinePoint {
  period: string
  frequency: number
}
