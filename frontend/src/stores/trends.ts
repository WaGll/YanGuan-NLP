/** 趋势分析 Pinia Store */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getTrends } from '@/api/trends'
import type { TrendData } from '@/types/trends'

export const useTrendsStore = defineStore('trends', () => {
  const data = ref<TrendData | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const seriesType = ref<string>('sentiment')
  const granularity = ref<string>('month')

  async function fetchTrends() {
    loading.value = true
    error.value = null
    try {
      data.value = await getTrends(seriesType.value, granularity.value)
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : '趋势数据加载失败'
      console.error('Trends fetch error:', err)
    } finally {
      loading.value = false
    }
  }

  function setSeriesType(type: string) {
    seriesType.value = type
    fetchTrends()
  }

  function setGranularity(gran: string) {
    granularity.value = gran
    fetchTrends()
  }

  return {
    data,
    loading,
    error,
    seriesType,
    granularity,
    fetchTrends,
    setSeriesType,
    setGranularity,
  }
})
