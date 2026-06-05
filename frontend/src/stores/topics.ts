/** 主题分析 Pinia Store */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getTopics, getTopicDetail } from '@/api/topics'
import type { TopicItem, TopicDetail } from '@/types/topics'

export const useTopicsStore = defineStore('topics', () => {
  const topics = ref<TopicItem[]>([])
  const selectedTopic = ref<TopicDetail | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const method = ref<string>('lda')

  async function fetchTopics() {
    loading.value = true
    error.value = null
    try {
      topics.value = await getTopics(method.value)
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : '主题数据加载失败'
      console.error('Topics fetch error:', err)
    } finally {
      loading.value = false
    }
  }

  function fetchTopicDetail(topic: TopicItem) {
    selectedTopic.value = getTopicDetail(topic)
  }

  function setMethod(newMethod: string) {
    method.value = newMethod
    fetchTopics()
  }

  return {
    topics,
    selectedTopic,
    loading,
    error,
    method,
    fetchTopics,
    fetchTopicDetail,
    setMethod,
  }
})
