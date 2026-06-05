<template>
  <div ref="chartRef" class="chart-container"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

export interface MLBarDataItem {
  model_name: string
  cv_mean: number
  cv_std: number
}

const props = defineProps<{
  data: MLBarDataItem[]
}>()

const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

function getChartOption(): echarts.EChartsOption {
  const models = props.data.map((d) => d.model_name)
  const means = props.data.map((d) => d.cv_mean)
  const stds = props.data.map((d) => d.cv_std)

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: unknown) => {
        const arr = params as Array<{ name: string; value: number }>
        let res = ''
        for (const item of arr) {
          res += `${item.name}: ${(item.value * 100).toFixed(2)}%<br/>`
        }
        return res
      },
    },
    grid: {
      left: 100,
      right: 40,
      top: 20,
      bottom: 30,
    },
    xAxis: {
      type: 'value',
      name: '准确率',
      min: 0,
      max: 1,
      axisLabel: {
        formatter: (v: number) => `${(v * 100).toFixed(0)}%`,
      },
    },
    yAxis: {
      type: 'category',
      data: models,
      axisLabel: {
        fontSize: 12,
      },
    },
    series: [
      {
        name: 'CV平均准确率',
        type: 'bar',
        data: means.map((m, i) => ({
          value: m,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: '#006D44' },
              { offset: 1, color: '#A6E7C9' },
            ]),
            borderRadius: [4, 4, 4, 4],
          },
        })),
        barWidth: 20,
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { type: 'dashed', color: '#006D44', width: 1.5 },
          data: stds.map((std, i) => ({
            yAxis: models[i],
            xAxis: means[i] + std,
            label: { show: false },
          })),
        },
        label: {
          show: true,
          position: 'right',
          formatter: (p: Record<string, unknown>) => `${(Number(p.value) * 100).toFixed(1)}%`,
          fontSize: 11,
        } as Record<string, unknown>,
      },
      {
        name: '标准差范围',
        type: 'bar',
        data: stds.map((std) => std * 2),
        barWidth: 14,
        barGap: '-100%',
        z: 0,
        itemStyle: {
          color: 'rgba(166, 231, 201, 0.3)',
          borderRadius: [4, 4, 4, 4],
        },
        label: { show: false },
        tooltip: { show: false },
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
  height: 350px;
}
</style>
