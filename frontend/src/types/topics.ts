/** 主题建模类型 */

export interface TopicKeyword {
  word: string
  weight: number
  rank: number
}

export interface TopicItem {
  topic_id: number
  topic_index: number
  label: string | null
  business_label: string | null
  coherence_score: number | null
  doc_count: number
  keywords: TopicKeyword[]
  representative_comments?: string[]
}

export interface TopicDetail {
  topic: TopicItem
  representative_comments: string[]
  keyword_count: number
}
