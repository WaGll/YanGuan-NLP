import client from './client'

export interface DashboardOverview {
  total_comments: number
  unique_users: number
  date_range_start: string | null
  date_range_end: string | null
  avg_sentiment: number
}

export async function fetchDashboard(): Promise<DashboardOverview> {
  const res = await client.get('/dashboard')
  return res.data
}
