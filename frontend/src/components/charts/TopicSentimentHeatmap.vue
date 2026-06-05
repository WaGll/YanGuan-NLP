<template>
  <div ref="chartRef" class="chart-container"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

export interface HeatmapCell {
  topic_label: string
  sentiment_class: string
  count: number
}

export interface HeatmapData {
  topics: string[]
  sentiment_classes: string[]
  cells: HeatmapCell[]
}

const props = defineProps<{
  data: HeatmapData
}>()

const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

function getChartOption(): echarts.EChartsOption {
  const yData = props.data.topics
  const xData = props.data.sentiment_classes

  const maxCount = Math.max(...props.data.cells.map((c) => c.count), 1)

  const seriesData = props.data.cells.map((cell) => {
    const xIdx = xData.indexOf(cell.sentiment_class)
    const yIdx = yData.indexOf(cell.topic_label)
    return [xIdx, yIdx, cell.count]
  })

  return {
    tooltip: {
      position: 'top',
      formatter: (params: unknown) => {
        const p = params as { data: [number, number, number] }
        const x = xData[p.data[0]]
        const y = yData[p.data[1]]
        const v = p.data[2]
        return `${y} × ${x}<br/>评论数: ${v}`
      },
    },
    grid: {
      left: 120,
      right: 40,
      top: 30,
      bottom: 60,
    },
    xAxis: {
      type: 'category',
      data: xData,
      position: 'top',
      axisLabel: {
        fontSize: 12,
        fontWeight: 'bold',
      },
      splitArea: { show: true },
    },
    yAxis: {
      type: 'category',
      data: yData,
      axisLabel: {
        width: 100,
        overflow: 'truncate',
        fontSize: 11,
      },
      splitArea: { show: true },
    },
    visualMap: {
      min: 0,
      max: maxCount,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 10,
      inRange: {
        color: ['#D4F5E5', '#A6E7C9', '#006D44'],
      },
      text: ['高', '低'],
      textStyle: {
        color: '#606266',
      },
    },
    series: [
      {
        type: 'heatmap',
        data: seriesData,
        label: {
          show: true,
          fontSize: 11,
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(0, 0, 0, 0.3)',
          },
        },
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
  height: 420px;
}
</style>
