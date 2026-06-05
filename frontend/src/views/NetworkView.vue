<template>
  <div class="network-page">
    <!-- Tab navigation -->
    <div class="network-tabs">
      <button
        class="network-tab"
        :class="{ 'network-tab--active': activeTab === 'graph' }"
        @click="activeTab = 'graph'"
      >Graph</button>
      <button
        class="network-tab"
        :class="{ 'network-tab--active': activeTab === 'metrics' }"
        @click="activeTab = 'metrics'; loadMetrics()"
      >Metrics</button>
    </div>

    <!-- ════════════════════════════════════════════════════════ -->
    <!-- TAB 1: Force Graph -->
    <!-- ════════════════════════════════════════════════════════ -->
    <template v-if="activeTab === 'graph'">
      <!-- Controls -->
      <div class="network-card">
        <div class="control-bar">
          <span class="control-label">Min Edge Weight</span>
          <el-slider
            v-model="store.minWeight"
            :min="0"
            :max="maxEdgeWeight"
            :step="1"
            show-input
            :show-input-controls="false"
            style="width: 240px"
          />
          <el-button size="small" @click="store.fetchNetwork" :loading="store.loading">
            Refresh
          </el-button>
        </div>
      </div>

      <!-- Loading / Error / Empty -->
      <template v-if="store.loading">
        <LoadingCard :rows="12" />
      </template>
      <el-alert
        v-else-if="store.error"
        :title="store.error"
        type="error"
        show-icon
        :closable="false"
        style="margin-bottom: 16px"
      />
      <div class="network-card" v-else-if="!store.data || store.data.nodes.length === 0">
        <el-empty description="No network data. Run the NLP pipeline first." />
      </div>

      <!-- Graph + Node Detail -->
      <el-row v-else :gutter="20">
        <el-col :xs="24" :lg="17">
          <div class="network-card network-card--chart">
            <NetworkForceGraph
              :graphData="filteredGraphData"
              @node-click="store.selectNode"
            />
          </div>
        </el-col>
        <el-col :xs="24" :lg="7">
          <div class="network-card" v-if="store.selectedNode">
            <h4 class="network-card__title">Node Detail</h4>
            <div class="node-detail">
              <div class="node-detail__row">
                <span class="node-detail__label">Name</span>
                <span class="node-detail__value"><strong>{{ store.selectedNode.name }}</strong></span>
              </div>
              <div class="node-detail__row">
                <span class="node-detail__label">Frequency</span>
                <span class="node-detail__value">{{ store.selectedNode.frequency }}</span>
              </div>
              <div class="node-detail__row">
                <span class="node-detail__label">Community</span>
                <span class="node-detail__value">{{ store.selectedNode.category }}</span>
              </div>
              <div class="node-detail__row">
                <span class="node-detail__label">Degree</span>
                <span class="node-detail__value">{{ store.selectedNode.degree_centrality?.toFixed(4) ?? '--' }}</span>
              </div>
              <div class="node-detail__row">
                <span class="node-detail__label">Betweenness</span>
                <span class="node-detail__value">{{ store.selectedNode.betweenness_centrality?.toFixed(4) ?? '--' }}</span>
              </div>
              <div class="node-detail__row">
                <span class="node-detail__label">PageRank</span>
                <span class="node-detail__value">{{ store.selectedNode.eigenvector_centrality?.toFixed(4) ?? '--' }}</span>
              </div>
            </div>
          </div>
          <div class="network-card network-card--empty" v-else>
            <el-icon :size="32" color="#cbd5e1"><InfoFilled /></el-icon>
            <p>Click a node<br>to see details</p>
          </div>
        </el-col>
      </el-row>
    </template>

    <!-- ════════════════════════════════════════════════════════ -->
    <!-- TAB 2: Metrics -->
    <!-- ════════════════════════════════════════════════════════ -->
    <template v-if="activeTab === 'metrics'">
      <!-- Loading -->
      <template v-if="store.metricsLoading">
        <LoadingCard :rows="6" />
      </template>

      <!-- Error -->
      <el-alert
        v-else-if="store.metricsError"
        :title="store.metricsError"
        type="error"
        show-icon
        :closable="false"
        style="margin-bottom: 16px"
      />

      <!-- Empty -->
      <div class="network-card" v-else-if="!store.metrics">
        <el-empty description="No metrics data. Build the network first." />
      </div>

      <!-- Content -->
      <template v-else-if="store.metrics">
        <!-- Statistics cards -->
        <el-row :gutter="20" style="margin-bottom: 20px">
          <el-col :xs="12" :sm="6" v-for="stat in statCards" :key="stat.label">
            <div class="network-card network-card--stat">
              <span class="stat-value">{{ stat.value }}</span>
              <span class="stat-label">{{ stat.label }}</span>
            </div>
          </el-col>
        </el-row>

        <!-- Centrality tables -->
        <el-row :gutter="20">
          <el-col :xs="24" :lg="12" v-for="metric in centralityMetrics" :key="metric.key">
            <div class="network-card">
              <h4 class="network-card__title">{{ metric.label }}</h4>
              <el-table
                :data="store.metrics.top_central_nodes[metric.key]"
                size="small"
              >
                <el-table-column type="index" label="#" width="48" />
                <el-table-column prop="word" label="Keyword" min-width="120" />
                <el-table-column prop="value" label="Score" width="90">
                  <template #default="{ row }">
                    {{ formatScore(row.value) }}
                  </template>
                </el-table-column>
                <el-table-column label="Relative" width="100">
                  <template #default="{ row }">
                    <el-progress
                      :percentage="getPercentage(row.value, metric.key)"
                      :color="'#16a34a'"
                      :show-text="false"
                      :stroke-width="6"
                    />
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </el-col>
        </el-row>

        <!-- Co-occurrence heatmap -->
        <div
          class="network-card"
          v-if="store.metrics.cooccurrence_matrix.keywords.length > 0"
        >
          <h4 class="network-card__title">Co-occurrence Matrix</h4>
          <div ref="matrixChartRef" class="matrix-chart"></div>
        </div>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { useNetworkStore } from '@/stores/network'
import type { GraphData } from '@/components/charts/NetworkForceGraph.vue'
import type { TopCentralNodes } from '@/types/network'
import NetworkForceGraph from '@/components/charts/NetworkForceGraph.vue'
import LoadingCard from '@/components/common/LoadingCard.vue'
import { InfoFilled } from '@element-plus/icons-vue'

const store = useNetworkStore()
const activeTab = ref<'graph' | 'metrics'>('graph')
const matrixChartRef = ref<HTMLElement | null>(null)
let matrixChartInstance: echarts.ECharts | null = null

// ── Graph tab ──
const maxEdgeWeight = computed(() => {
  if (!store.data || store.data.edges.length === 0) return 10
  return Math.max(...store.data.edges.map((e) => e.weight), 1)
})

const filteredGraphData = computed<GraphData>(() => {
  if (!store.data) return { nodes: [], edges: [] }
  const filteredEdges = store.data.edges.filter((e) => e.weight >= store.minWeight)
  const connectedNodeIds = new Set<string>()
  for (const e of filteredEdges) {
    connectedNodeIds.add(e.source)
    connectedNodeIds.add(e.target)
  }
  let filteredNodes = store.data.nodes.filter((n) => connectedNodeIds.has(n.id))
  // Limit to top 75 nodes by degree for readability
  filteredNodes = filteredNodes
    .sort((a, b) => b.symbolSize - a.symbolSize)
    .slice(0, 75)
  const topIds = new Set(filteredNodes.map((n) => n.id))
  const topEdges = filteredEdges.filter((e) => topIds.has(e.source) && topIds.has(e.target))
  return {
    nodes: filteredNodes.map((n) => ({
      id: n.id,
      name: n.name,
      symbolSize: n.symbolSize,
      category: n.category,
    })),
    edges: topEdges,
  }
})

// ── Metrics tab ──
const statCards = computed(() => {
  const s = store.metrics?.statistics
  if (!s) return []
  return [
    { label: 'Nodes', value: s.node_count },
    { label: 'Edges', value: s.edge_count },
    { label: 'Density', value: s.density.toFixed(4) },
    { label: 'Communities', value: s.community_count },
  ]
})

const centralityMetrics = [
  { key: 'degree' as const, label: 'Degree Centrality' },
  { key: 'betweenness' as const, label: 'Betweenness Centrality' },
  { key: 'closeness' as const, label: 'Closeness Centrality' },
  { key: 'pagerank' as const, label: 'PageRank' },
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
        return `${m.keywords[val[0]]} ↔ ${m.keywords[val[1]]}<br/>Co-occurrence: ${val[2]}`
      },
    },
    grid: { left: 100, right: 40, top: 20, bottom: 100 },
    xAxis: {
      type: 'category',
      data: m.keywords,
      axisLabel: { rotate: 45, fontSize: 10, color: '#94a3b8' },
    },
    yAxis: {
      type: 'category',
      data: m.keywords,
      axisLabel: { fontSize: 10, color: '#94a3b8' },
    },
    visualMap: {
      min: 0,
      max: Math.max(...data.map((d) => d[2]), 1),
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      inRange: { color: ['#dcfce7', '#16a34a', '#14532d'] },
    },
    series: [{
      type: 'heatmap',
      data,
      label: { show: false },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.25)' } },
    }],
  })
}

function handleResize() {
  matrixChartInstance?.resize()
}

function loadMetrics() {
  if (!store.metrics && !store.metricsLoading) {
    store.fetchMetrics()
  }
}

watch(() => store.metrics, () => {
  if (store.metrics && activeTab.value === 'metrics') {
    nextTick(() => setTimeout(renderMatrixChart, 200))
  }
})

watch(activeTab, (tab) => {
  if (tab === 'metrics' && store.metrics) {
    nextTick(() => setTimeout(renderMatrixChart, 200))
  }
})

onMounted(() => {
  store.fetchNetwork()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  matrixChartInstance?.dispose()
})
</script>

<style scoped>
/* ── Tabs ── */
.network-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
  background: #ffffff;
  border-radius: 24px;
  padding: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
  width: fit-content;
}

.network-tab {
  height: 36px;
  padding: 0 20px;
  border-radius: 20px;
  border: none;
  background: transparent;
  color: #64748b;
  font-size: 13px;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.15s ease;
}

.network-tab:hover {
  color: #1e293b;
}

.network-tab--active {
  background: #f5f5f5;
  color: #1e293b;
  font-weight: 600;
}

/* ── Card (matches global card style) ── */
.network-card {
  background: #ffffff;
  border-radius: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
  padding: 24px 28px;
  margin-bottom: 20px;
}

.network-card--chart {
  padding: 12px;
}

.network-card--empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 240px;
  color: #94a3b8;
  font-size: 13px;
}

.network-card--stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.network-card__title {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 16px 0;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #1e293b;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}

.stat-label {
  font-size: 12px;
  color: #94a3b8;
}

/* ── Control bar ── */
.control-bar {
  display: flex;
  align-items: center;
  gap: 16px;
}

.control-label {
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
  white-space: nowrap;
}

/* ── Node detail ── */
.node-detail {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.node-detail__row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.node-detail__label {
  font-size: 12px;
  color: #94a3b8;
}

.node-detail__value {
  font-size: 13px;
  color: #1e293b;
  font-variant-numeric: tabular-nums;
}

/* ── Heatmap ── */
.matrix-chart {
  width: 100%;
  height: 480px;
}
</style>
