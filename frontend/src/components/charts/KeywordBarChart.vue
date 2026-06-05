<template>
  <div ref="chartRef" class="chart-container"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

export interface KeywordDataItem {
  word: string
  frequency: number
}

const props = defineProps<{
  data: KeywordDataItem[]
}>()

const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

function getChartOption(): echarts.EChartsOption {
  const sorted = [...props.data].sort((a, b) => a.frequency - b.frequency)
  const items = sorted.slice(-20)
  const maxVal = items.length > 0 ? items[items.length - 1].frequency : 1
  const prevMax = items.length > 1 ? items[items.length - 2].frequency : maxVal

  // Delta for floating badge on top bar
  const delta = maxVal > 0 && prevMax > 0
    ? ((maxVal - prevMax) / prevMax * 100).toFixed(1)
    : null

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: '#ffffff',
      borderColor: '#f0f1f3',
      textStyle: { color: '#1e293b', fontSize: 12 },
      formatter: (params: unknown) => {
        const p = (params as Array<{ name: string; value: number }>)[0]
        return `<strong>${p.name}</strong><br/>Frequency: ${p.value.toLocaleString()}`
      },
    },
    grid: {
      left: 100,
      right: 60,
      top: 16,
      bottom: 12,
    },
    xAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
      axisLabel: { color: '#94a3b8', fontSize: 10 },
    },
    yAxis: {
      type: 'category',
      data: items.map((d) => d.word),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        fontSize: 12,
        color: '#64748b',
        fontWeight: 500,
      },
      inverse: true,
    },
    series: [{
      type: 'bar',
      barWidth: 20,
      barCategoryGap: '30px',
      data: items.map((d, i) => {
        const isTop = i === items.length - 1
        return {
          value: d.frequency,
          itemStyle: {
            color: isTop ? '#16a34a' : '#b7d7c5',
            borderRadius: [9999, 9999, 9999, 9999],
            decal: {
              symbol: 'diamond',
              symbolSize: 0.6,
              color: 'rgba(255,255,255,0.25)',
              dashArrayX: [3, 6],
              dashArrayY: [1, 3],
              rotation: -0.45,
            },
          },
          emphasis: {
            itemStyle: {
              color: '#16a34a',
              shadowBlur: 12,
              shadowColor: 'rgba(22, 163, 74, 0.35)',
            },
          },
          label: isTop && delta ? {
            show: true,
            position: 'right',
            distance: 8,
            color: '#16a34a',
            fontSize: 11,
            fontWeight: 600,
            formatter: `+${delta}%`,
            backgroundColor: '#f0fdf4',
            padding: [2, 8],
            borderRadius: 9999,
          } : undefined,
        }
      }),
    }],
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
  height: 420px;
}
</style>
