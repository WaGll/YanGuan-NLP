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
  '#3ba272',
  '#fc8452',
  '#9a60b4',
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
            fontSize: 10,
          },
        })),
        edges: props.graphData.edges.map((e) => ({
          source: e.source,
          target: e.target,
          value: e.weight,
          lineStyle: {
            width: Math.max(0.5, (e.weight / maxWeight) * 5),
            curveness: 0.1,
            opacity: 0.5,
          },
        })),
        categories: [...new Set(props.graphData.nodes.map((n) => n.category))].map((c, i) => ({
          name: `类别 ${c}`,
          itemStyle: { color: categoryColors[i % categoryColors.length] },
        })),
        force: {
          repulsion: 300,
          gravity: 0.1,
          edgeLength: [80, 200],
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
  chartInstance.setOption(getChartOption())

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

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
})

watch(
  () => props.graphData,
  () => {
    if (chartInstance) {
      chartInstance.setOption(getChartOption())
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
