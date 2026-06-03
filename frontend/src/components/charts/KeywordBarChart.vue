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
  const top = sorted.slice(-20)

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: unknown) => {
        const p = (params as Array<{ name: string; value: number }>)[0]
        return `${p.name}: ${p.value}`
      },
    },
    grid: {
      left: 100,
      right: 40,
      top: 10,
      bottom: 60,
    },
    xAxis: {
      type: 'value',
      name: '频次',
    },
    yAxis: {
      type: 'category',
      data: top.map((d) => d.word),
      axisLabel: {
        rotate: 45,
        fontSize: 11,
        align: 'right',
      },
      inverse: true,
    },
    series: [
      {
        type: 'bar',
        data: top.map((d) => ({
          value: d.frequency,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: '#409eff' },
              { offset: 1, color: '#a0cfff' },
            ]),
            borderRadius: [0, 4, 4, 0],
          },
        })),
        barWidth: 16,
        label: {
          show: true,
          position: 'right',
          fontSize: 10,
        },
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
  height: 400px;
}
</style>
