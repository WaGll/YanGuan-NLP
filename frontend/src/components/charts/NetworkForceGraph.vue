<template>
  <div ref="chartRef" class="chart-container"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

export interface GraphNode {
  id: string
  name: string
  symbolSize: number
  category: number
}

export interface GraphEdge {
  source: string
  target: string
  weight: number
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

const props = defineProps<{
  graphData: GraphData
}>()

const emit = defineEmits<{
  nodeClick: [nodeId: string]
}>()

const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

const categoryColors = [
  '#5470c6',
  '#91cc75',
  '#fac858',
  '#ee6666',
  '#73c0de',
  '#fc8452',
  '#9a60b4',
  '#ea7ccc',
]

function getChartOption(): echarts.EChartsOption {
  const maxWeight = Math.max(...props.graphData.edges.map((e) => e.weight), 1)

  return {
    tooltip: {
      trigger: 'item',
      formatter: (params: unknown) => {
        const p = params as { dataType?: string; name: string; value?: string }
        if (p.dataType === 'edge') {
          return `${p.name}: 权重 ${p.value}`
        }
        return `节点: ${p.name}`
      },
    },
    legend: {
      data: [...new Set(props.graphData.nodes.map((n) => String(n.category)))].map((c) => ({
        name: `类别 ${c}`,
      })),
      bottom: 10,
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        animation: true,
        roam: true,
        draggable: true,
        data: props.graphData.nodes.map((n) => ({
          id: n.id,
          name: n.name,
          symbolSize: n.symbolSize || 30,
          category: n.category,
          itemStyle: {
            color: categoryColors[n.category % categoryColors.length],
          },
          label: {
            show: true,
            fontSize: 9,
            color: '#64748b',
            overflow: 'truncate',
            width: 60,
          },
        })),
        edges: props.graphData.edges.map((e) => ({
          source: e.source,
          target: e.target,
          value: e.weight,
          lineStyle: {
            width: Math.max(1.2, Math.sqrt(e.weight / maxWeight) * 4),
            curveness: 0.1,
            opacity: 0.65,
            color: '#94a3b8',
          },
        })),
        categories: [...new Set(props.graphData.nodes.map((n) => n.category))].map((c, i) => ({
          name: `类别 ${c}`,
          itemStyle: { color: categoryColors[i % categoryColors.length] },
        })),
        force: {
          repulsion: 500,
          gravity: 0.08,
          edgeLength: [100, 260],
          layoutAnimation: true,
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: { width: 6 },
        },
      },
    ],
  }
}

function initChart() {
  if (!chartRef.value) return
  chartInstance = echarts.init(chartRef.value)
  chartInstance.setOption(getChartOption(), { notMerge: true })

  chartInstance.on('click', (params: unknown) => {
    const p = params as { dataType?: string; data?: { id: string } }
    if (p.dataType === 'node' && p.data?.id) {
      emit('nodeClick', p.data.id)
    }
  })
}

function handleResize() {
  chartInstance?.resize()
}

function resetView() {
  if (chartInstance) {
    chartInstance.dispatchAction({ type: 'restore' })
  }
}

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
})

defineExpose({ resetView })

watch(
  () => props.graphData,
  () => {
    if (chartInstance) {
      chartInstance.setOption(getChartOption(), { notMerge: true })
    }
  },
  { deep: true }
)
</script>

<style scoped>
.chart-container {
  width: 100%;
  height: 550px;
}
</style>
