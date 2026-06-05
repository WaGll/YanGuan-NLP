<template>
  <div class="network-analytics-page">
    <h2 class="page-title">网络分析</h2>

    <!-- 加载状态 -->
    <template v-if="store.metricsLoading">
      <LoadingCard :rows="6" />
    </template>

    <!-- 错误状态 -->
    <el-alert
      v-else-if="store.metricsError"
      :title="store.metricsError"
      type="error"
      show-icon
      :closable="false"
      style="margin-bottom: 20px"
    />

    <!-- 正常内容 -->
    <template v-else-if="store.metrics">
      <!-- 网络统计 -->
      <el-row :gutter="24" style="margin-bottom: 20px">
        <el-col :xs="12" :sm="6" v-for="stat in statCards" :key="stat.label">
          <StatCard
            :title="stat.label"
            :value="stat.value"
            :icon="stat.icon"
            :color="stat.color"
          />
        </el-col>
      </el-row>

      <!-- Top 中心节点表格 -->
      <el-row :gutter="20">
        <el-col :xs="24" :lg="12" v-for="metric in centralityMetrics" :key="metric.key">
          <el-card style="margin-bottom: 20px">
            <template #header>
              <span>{{ metric.label }}</span>
            </template>
            <el-table
              :data="store.metrics.top_central_nodes[metric.key]"
              stripe
              size="small"
            >
              <el-table-column type="index" label="#" width="50" />
              <el-table-column prop="word" label="关键词" min-width="120" />
              <el-table-column prop="value" label="得分" width="100">
                <template #default="{ row }">
                  {{ formatScore(row.value) }}
                </template>
              </el-table-column>
              <el-table-column label="占比" width="120">
                <template #default="{ row }">
                  <el-progress
                    :percentage="getPercentage(row.value, metric.key)"
                    :color="metric.color"
                    :show-text="false"
                  />
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
      </el-row>

      <!-- 共现矩阵热力图 -->
      <el-card v-if="store.metrics.cooccurrence_matrix.keywords.length > 0" style="margin-bottom: 20px">
        <template #header>
          <span>关键词共现矩阵</span>
        </template>
        <div ref="matrixChartRef" class="matrix-chart"></div>
        <el-empty
          v-if="!hasCooccurrenceData"
          description="暂无共现数据，请先运行网络构建"
        />
      </el-card>
    </template>

    <!-- 空数据 -->
    <el-empty
      v-else
      description="暂无网络分析数据，请先在「共现网络」页面构建网络"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { useNetworkStore } from '@/stores/network'
import LoadingCard from '@/components/common/LoadingCard.vue'
import StatCard from '@/components/common/StatCard.vue'
import type { TopCentralNodes } from '@/types/network'

const store = useNetworkStore()
const matrixChartRef = ref<HTMLElement | null>(null)
let matrixChartInstance: echarts.ECharts | null = null

// 统计卡片数据
const statCards = computed(() => {
  const s = store.metrics?.statistics
  if (!s) return []
  return [
    { label: '节点数', value: s.node_count, icon: 'Share', color: '#006D44' },
    { label: '边数', value: s.edge_count, icon: 'Connection', color: '#1A8A5A' },
    { label: '网络密度', value: s.density.toFixed(4), icon: 'DataAnalysis', color: '#3DA775' },
    { label: '社区数', value: s.community_count, icon: 'Grid', color: '#A6E7C9' },
  ]
})

// 中心性指标配置
const centralityMetrics = [
  { key: 'degree' as const, label: 'Degree Centrality（度中心性）', color: '#006D44' },
  { key: 'betweenness' as const, label: 'Betweenness Centrality（介数中心性）', color: '#1A8A5A' },
  { key: 'closeness' as const, label: 'Closeness Centrality（接近中心性）', color: '#3DA775' },
  { key: 'pagerank' as const, label: 'PageRank', color: '#A6E7C9' },
]

function formatScore(value: number): string {
  if (value === 0) return '0'
  return value < 0.01 ? value.toExponential(2) : value.toFixed(4)
}

function getPercentage(value: number, metricKey: keyof TopCentralNodes): number {
  const nodes = store.metrics?.top_central_nodes[metricKey]
  if (!nodes || nodes.length === 0) return 0
  const maxVal = nodes[0]?.value ?? 1
  if (maxVal === 0) return 0
  return Math.round((value / maxVal) * 100)
}

const hasCooccurrenceData = computed(() => {
  const m = store.metrics?.cooccurrence_matrix
  if (!m || m.keywords.length === 0) return false
  return m.matrix.some((row) => row.some((v) => v > 0))
})

// 共现矩阵热力图
function renderMatrixChart() {
  const m = store.metrics?.cooccurrence_matrix
  if (!m || !matrixChartRef.value || m.keywords.length === 0) return

  if (!matrixChartInstance) {
    matrixChartInstance = echarts.init(matrixChartRef.value)
  }

  const data: [number, number, number][] = []
  for (let i = 0; i < m.keywords.length; i++) {
    for (let j = 0; j < m.keywords.length; j++) {
      if (m.matrix[i]?.[j]) {
        data.push([i, j, m.matrix[i][j]])
      }
    }
  }

  matrixChartInstance.setOption({
    tooltip: {
      formatter: (p: any) => {
        const val = p.value as [number, number, number] | undefined
        if (!val) return ''
        const xIdx = val[0]
        const yIdx = val[1]
        const count = val[2]
        return `${m.keywords[xIdx]} ↔ ${m.keywords[yIdx]}\n共现次数: ${count}`
      },
    },
    grid: { left: 100, right: 40, top: 20, bottom: 100 },
    xAxis: {
      type: 'category',
      data: m.keywords,
      axisLabel: { rotate: 45, fontSize: 10 },
    },
    yAxis: {
      type: 'category',
      data: m.keywords,
      axisLabel: { fontSize: 10 },
    },
    visualMap: {
      min: 0,
      max: Math.max(...data.map((d) => d[2]), 1),
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      inRange: {
        color: ['#D4F5E5', '#006D44', '#0D3D24'],
      },
    },
    series: [
      {
        type: 'heatmap',
        data,
        label: { show: false },
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' },
        },
      },
    ],
  })
}

function handleResize() {
  matrixChartInstance?.resize()
}

watch(() => store.metrics, () => {
  if (store.metrics) {
    // 延迟渲染等待 DOM 更新
    setTimeout(renderMatrixChart, 200)
  }
})

onMounted(() => {
  store.fetchMetrics()
})

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  matrixChartInstance?.dispose()
})
</script>

<style scoped>
.matrix-chart {
  width: 100%;
  height: 500px;
}
</style>
