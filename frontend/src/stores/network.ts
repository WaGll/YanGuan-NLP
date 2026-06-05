/** 语义网络 Pinia Store */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getNetworkData, getNetworkMetrics } from '@/api/network'
import type { NetworkData, NetworkMetrics, NetworkNode } from '@/types/network'

export const useNetworkStore = defineStore('network', () => {
  const data = ref<NetworkData | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const selectedNode = ref<NetworkNode | null>(null)
  const minWeight = ref(2)
  const maxNodes = ref(200)

  // 网络指标
  const metrics = ref<NetworkMetrics | null>(null)
  const metricsLoading = ref(false)
  const metricsError = ref<string | null>(null)

  async function fetchNetwork() {
    loading.value = true
    error.value = null
    try {
      data.value = await getNetworkData(minWeight.value, maxNodes.value)
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : '网络数据加载失败'
      console.error('Network fetch error:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchMetrics(topN: number = 20) {
    metricsLoading.value = true
    metricsError.value = null
    try {
      metrics.value = await getNetworkMetrics(topN)
    } catch (err: unknown) {
      metricsError.value = err instanceof Error ? err.message : '网络指标加载失败'
      console.error('Network metrics fetch error:', err)
    } finally {
      metricsLoading.value = false
    }
  }

  function selectNode(nodeId: string) {
    const node = data.value?.nodes.find((n) => n.id === nodeId)
    selectedNode.value = node ?? null
  }

  function clearSelection() {
    selectedNode.value = null
  }

  function setMinWeight(weight: number) {
    minWeight.value = weight
  }

  return {
    data,
    loading,
    error,
    selectedNode,
    minWeight,
    maxNodes,
    metrics,
    metricsLoading,
    metricsError,
    fetchNetwork,
    fetchMetrics,
    selectNode,
    clearSelection,
    setMinWeight,
  }
})
