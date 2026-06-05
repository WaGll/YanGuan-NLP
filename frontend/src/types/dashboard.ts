/** 仪表盘类型 */

export interface DashboardOverview {
  total_comments: number
  unique_users: number
  date_range_start: string | null
  date_range_end: string | null
  avg_sentiment: number | null
  top_keywords: string[]
}
