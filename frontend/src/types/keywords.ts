/** 关键词类型 */

export interface KeywordItem {
  word: string
  frequency: number
  tfidf_score: number | null
}

export interface WordcloudItem {
  name: string
  value: number
}

export interface KeywordsData {
  keywords: KeywordItem[]
  wordcloud_data: WordcloudItem[]
  total: number
}
