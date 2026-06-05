/** 主题×情感联合分析 Pinia Store */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getTopicSentimentMatrix } from '@/api/topicSentiment'
import type { TopicSentimentData } from '@/types/topic-sentiment'

export const useTopicSentimentStore = defineStore('topicSentiment', () => {
  const data = ref<TopicSentimentData | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const method = ref<string>('lda')

  async function fetchMatrix() {
    loading.value = true
    error.value = null
    try {
      data.value = await getTopicSentimentMatrix(method.value)
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : '主题情感数据加载失败'
      console.error('TopicSentiment fetch error:', err)
    } finally {
      loading.value = false
    }
  }

  function setMethod(newMethod: string) {
    method.value = newMethod
    fetchMatrix()
  }

  return { data, loading, error, method, fetchMatrix, setMethod }
})
