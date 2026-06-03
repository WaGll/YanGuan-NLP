import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  fetchSentiment,
  fetchMLScores,
  type SentimentDistribution,
  type MLScore,
} from '@/api/sentiment'

export const useSentimentStore = defineStore('sentiment', () => {
  const distribution = ref<SentimentDistribution | null>(null)
  const mlScores = ref<MLScore[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchDistribution() {
    loading.value = true
    error.value = null
    try {
      distribution.value = await fetchSentiment()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '获取情感分布数据失败'
      error.value = msg
      console.error('Sentiment distribution fetch error:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchMLScoresAction() {
    loading.value = true
    error.value = null
    try {
      mlScores.value = await fetchMLScores()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '获取ML模型数据失败'
      error.value = msg
      console.error('ML scores fetch error:', err)
    } finally {
      loading.value = false
    }
  }

  return {
    distribution,
    mlScores,
    loading,
    error,
    fetchDistribution,
    fetchMLScores: fetchMLScoresAction,
  }
})
