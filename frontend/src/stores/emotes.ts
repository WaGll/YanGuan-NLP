/** 表情分析 Pinia Store */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  fetchEmoteDistribution,
  fetchEmoteDetail,
  fetchEmoteSentimentCorrelation,
  fetchEmoteWordcloud,
} from '@/api/emotes'
import type {
  EmoteDistributionData,
  EmoteDetail,
  EmoteItem,
  EmoteSentimentCorrelation,
} from '@/types/emotes'

export const useEmotesStore = defineStore('emotes', () => {
  const emotes = ref<EmoteItem[]>([])
  const distribution = ref<EmoteDistributionData | null>(null)
  const correlations = ref<EmoteSentimentCorrelation[]>([])
  const wordcloudData = ref<{ name: string; value: number }[]>([])
  const selectedEmote = ref<EmoteDetail | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const sortBy = ref<string>('frequency')

  async function fetchDistribution() {
    loading.value = true
    error.value = null
    try {
      const data = await fetchEmoteDistribution(sortBy.value, 50)
      distribution.value = data
      emotes.value = data.emotes
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : '表情数据加载失败'
      console.error('Emote distribution fetch error:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchCorrelations() {
    try {
      correlations.value = await fetchEmoteSentimentCorrelation()
    } catch (err: unknown) {
      console.error('Emote correlation fetch error:', err)
    }
  }

  async function fetchDetail(name: string) {
    try {
      selectedEmote.value = await fetchEmoteDetail(name)
    } catch (err: unknown) {
      console.error('Emote detail fetch error:', err)
    }
  }

  async function fetchWordcloud() {
    try {
      wordcloudData.value = await fetchEmoteWordcloud(100)
    } catch (err: unknown) {
      console.error('Emote wordcloud fetch error:', err)
    }
  }

  function setSortBy(newSortBy: string) {
    sortBy.value = newSortBy
    fetchDistribution()
  }

  return {
    emotes,
    distribution,
    correlations,
    wordcloudData,
    selectedEmote,
    loading,
    error,
    sortBy,
    fetchDistribution,
    fetchCorrelations,
    fetchDetail,
    fetchWordcloud,
    setSortBy,
  }
})
