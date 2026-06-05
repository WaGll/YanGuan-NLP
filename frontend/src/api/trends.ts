/** 趋势分析 API 模块 */

import client from './client'
import type { TrendData } from '@/types/trends'

export async function getTrends(
  seriesType: string = 'sentiment',
  granularity: string = 'month'
): Promise<TrendData> {
  const res = await client.get('/trends', {
    params: { series_type: seriesType, granularity },
  })
  // 后端返回扁平数组 {data: [...]}，前端期望 {buckets, ...} 对象
  const buckets = Array.isArray(res.data) ? res.data : (res.data?.buckets ?? [])
  return {
    series_type: seriesType,
    granularity,
    buckets,
    total_points: buckets.length,
  }
}
