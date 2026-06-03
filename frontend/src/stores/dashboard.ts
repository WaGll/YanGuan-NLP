import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchDashboard, type DashboardOverview } from '@/api/dashboard'

export const useDashboardStore = defineStore('dashboard', () => {
  const stats = ref<DashboardOverview | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchStats() {
    loading.value = true
    error.value = null
    try {
      stats.value = await fetchDashboard()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '获取仪表盘数据失败'
      error.value = msg
      console.error('Dashboard fetch error:', err)
    } finally {
      loading.value = false
    }
  }

  return { stats, loading, error, fetchStats }
})
