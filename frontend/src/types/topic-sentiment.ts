/** 主题×情感联合分析类型 */

export interface JointMatrixCell {
  topic: string
  sentiment: string
  count: number
  proportion: number
}

export interface TopicSentimentData {
  topics: string[]
  topic_business_labels: string[]
  sentiment_classes: string[]
  cells: JointMatrixCell[]
}
