<template>
  <div ref="chartRef" class="chart-container"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

export interface TrendDataItem {
  bucket_start: string
  value: number
  comment_count: number
}

const props = defineProps<{
  data: TrendDataItem[]
  title: string
}>()

const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

function getChartOption(): echarts.EChartsOption {
  const timestamps = props.data.map((d) => d.bucket_start)
  const values = props.data.map((d) => d.value)
  const counts = props.data.map((d) => d.comment_count)

  return {
    title: {
      text: props.title,
      left: 'center',
      top: 5,
      textStyle: { fontSize: 14, fontWeight: 500 },
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: unknown) => {
        const arr = params as Array<{ axisValue: string; seriesName: string; value: number }>
        let res = `${arr[0]?.axisValue || ''}<br/>`
        for (const item of arr) {
          res += `${item.seriesName}: ${item.value}<br/>`
        }
        return res
      },
    },
    legend: {
      data: [props.title, '评论数'],
      bottom: 5,
    },
    grid: {
      left: 50,
      right: 50,
      top: 50,
      bottom: 40,
    },
    xAxis: {
      type: 'category',
      data: timestamps,
      boundaryGap: false,
      axisLabel: {
        rotate: 30,
        fontSize: 10,
      },
    },
    yAxis: {
      type: 'value',
      name: props.title,
    },
    series: [
      {
        name: props.title,
        type: 'line',
        data: values,
        smooth: true,
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
            { offset: 1, color: 'rgba(64, 158, 255, 0.05)' },
          ]),
        },
        lineStyle: {
          color: '#409eff',
          width: 2,
        },
        itemStyle: {
          color: '#409eff',
        },
        symbol: 'circle',
        symbolSize: 6,
      },
      {
        name: '评论数',
        type: 'bar',
        data: counts,
        yAxisIndex: 0,
        barWidth: 8,
        itemStyle: {
          color: 'rgba(144, 147, 153, 0.4)',
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
  () => [props.data, props.title],
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
