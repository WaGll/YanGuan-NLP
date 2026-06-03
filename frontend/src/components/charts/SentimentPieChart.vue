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
  negative: '#f56c6c',
  neutral: '#909399',
  positive: '#67c23a',
  负面: '#f56c6c',
  中性: '#909399',
  正面: '#67c23a',
}

function getChartOption(): echarts.EChartsOption {
  return {
    tooltip: {
      trigger: 'item',
      formatter: (params: unknown) => {
        const p = params as { name: string; value: number; percent: number }
        return `${p.name}: ${p.value} 条 (${p.percent}%)`
      },
    },
    legend: {
      bottom: 10,
      data: props.data.map((d) => d.label),
    },
    series: [
      {
        name: '情感分布',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 4,
          borderColor: '#fff',
          borderWidth: 2,
        },
        label: {
          show: true,
          formatter: '{b}\n{d}%',
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 16,
            fontWeight: 'bold',
          },
        },
        data: props.data.map((d) => ({
          name: d.label,
          value: d.count,
          itemStyle: {
            color: colorMap[d.label] || '#409eff',
          },
        })),
      },
    ],
  }
}

function initChart() {
  if (!chartRef.value) return
  chartInstance = echarts.init(chartRef.value)
  chartInstance.setOption(getChartOption())
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
      chartInstance.setOption(getChartOption())
    }
  },
  { deep: true }
)
</script>

<style scoped>
.chart-container {
  width: 100%;
  height: 350px;
}
</style>
