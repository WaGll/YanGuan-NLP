<template>
  <div ref="chartRef" class="chart-container"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

export interface PieDataItem {
  label: string
  count: number
  percentage: number
}

const props = defineProps<{
  data: PieDataItem[]
}>()

const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

const colorMap: Record<string, string> = {
  negative: '#ef4444',
  neutral: '#f59e0b',
  positive: '#16a34a',
  负面: '#ef4444',
  中性: '#f59e0b',
  正面: '#16a34a',
}

function getChartOption(): echarts.EChartsOption {
  return {
    tooltip: {
      trigger: 'item',
      backgroundColor: '#ffffff',
      borderColor: '#f0f1f3',
      textStyle: { color: '#1e293b', fontSize: 12 },
      formatter: (params: unknown) => {
        const p = params as { name: string; value: number; percent: number }
        return `${p.name}: ${p.value.toLocaleString()} (${p.percent}%)`
      },
    },
    series: [
      {
        name: 'Sentiment',
        type: 'pie',
        radius: ['58%', '80%'],
        center: ['50%', '48%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 8,
          borderColor: '#ffffff',
          borderWidth: 3,
        },
        label: {
          show: true,
          position: 'outside',
          formatter: '{b}\n{d}%',
          fontSize: 11,
          color: '#64748b',
          lineHeight: 16,
        },
        labelLine: {
          length: 18,
          length2: 28,
          lineStyle: { color: '#cbd5e1' },
        },
        emphasis: {
          scaleSize: 8,
          label: { show: true, fontSize: 14, fontWeight: 'bold' },
        },
        data: props.data.map((d) => ({
          name: d.label,
          value: d.count,
          itemStyle: { color: colorMap[d.label] || '#94a3b8' },
        })),
      },
    ],
  }
}

function initChart() {
  if (!chartRef.value) return
  chartInstance = echarts.init(chartRef.value)
  chartInstance.setOption(getChartOption(), { notMerge: true })
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
  () => props.data,
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
  height: 320px;
}
</style>
