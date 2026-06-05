<template>
  <div ref="chartRef" class="chart-container"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import 'echarts-wordcloud'

export interface WordCloudItem {
  name: string
  value: number
}

const props = withDefaults(defineProps<{
  data: WordCloudItem[]
  maxWords?: number
}>(), {
  maxWords: 80,
})

const emit = defineEmits<{
  'word-click': [item: WordCloudItem]
}>()

const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

const COLORS = [
  '#1e3a5f', '#475569', '#b8860b', '#722f37',
  '#166534', '#334155', '#92400e', '#3b5998',
  '#5b2c6f', '#1a5276', '#7d6608', '#943126',
]

function createGraduationCapMask(): HTMLImageElement {
  const s = 256
  const canvas = document.createElement('canvas')
  canvas.width = s
  canvas.height = s
  const ctx = canvas.getContext('2d')!

  ctx.fillStyle = '#ffffff'

  // Cap board (trapezoid at top)
  const bx = 40, by = 36, bw = s - 80, bh = 40
  ctx.beginPath()
  ctx.moveTo(bx, by + bh)
  ctx.lineTo(bx + 14, by)
  ctx.lineTo(bx + bw - 14, by)
  ctx.lineTo(bx + bw, by + bh)
  ctx.closePath()
  ctx.fill()

  // Skull cap (rounded dome below)
  ctx.beginPath()
  ctx.moveTo(bx + 36, by + bh)
  ctx.quadraticCurveTo(s / 2, s - 48, bx + bw - 36, by + bh)
  ctx.closePath()
  ctx.fill()

  // Tassel line
  ctx.beginPath()
  ctx.moveTo(bx + bw - 28, by + bh - 4)
  ctx.quadraticCurveTo(bx + bw - 8, by + 70, bx + bw - 16, by + 90)
  ctx.lineWidth = 5
  ctx.strokeStyle = '#ffffff'
  ctx.stroke()

  // Tassel knot
  ctx.beginPath()
  ctx.arc(bx + bw - 16, by + 90, 10, 0, Math.PI * 2)
  ctx.fill()

  const img = new Image()
  img.src = canvas.toDataURL()
  return img
}

function getChartOption(maskImg: HTMLImageElement): echarts.EChartsOption {
  const items = [...props.data]
    .sort((a, b) => b.value - a.value)
    .slice(0, props.maxWords)

  if (items.length === 0) return {}

  const maxVal = items[0]?.value ?? 1

  return {
    tooltip: {
      show: true,
      backgroundColor: '#ffffff',
      borderColor: '#f0f1f3',
      textStyle: { color: '#1e293b', fontSize: 12 },
      formatter: (p: any) => `${p.name}: ${p.value}`,
    },
    series: [{
      type: 'wordCloud',
      maskImage: maskImg,
      width: '95%',
      height: '90%',
      sizeRange: [14, 56],
      rotationRange: [-45, 45],
      rotationStep: 45,
      gridSize: 8,
      drawOutOfBound: false,
      layoutAnimation: true,
      textStyle: {
        fontFamily: 'Inter, PingFang SC, Microsoft YaHei, sans-serif',
        fontWeight: '600',
        color: () => COLORS[Math.floor(Math.random() * COLORS.length)],
      },
      emphasis: {
        textStyle: {
          fontSize: 20,
          fontWeight: 'bold' as const,
        },
      },
      data: items.map((d) => ({
        name: d.name,
        value: d.value,
      })),
    }],
  }
}

function initOrUpdateChart(maskImg: HTMLImageElement) {
  if (!chartRef.value) return
  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
    chartInstance.on('click', (params: any) => {
      if (params.name) {
        emit('word-click', { name: params.name, value: params.value })
      }
    })
  }
  chartInstance.setOption(getChartOption(maskImg), { notMerge: true })
  chartInstance.resize()
}

function initChart() {
  if (!chartRef.value || props.data.length === 0) return
  const maskImg = createGraduationCapMask()
  if (maskImg.complete) {
    initOrUpdateChart(maskImg)
  } else {
    maskImg.onload = () => initOrUpdateChart(maskImg)
  }
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

watch(() => props.data, () => {
  if (chartInstance) {
    const maskImg = createGraduationCapMask()
    const applyOption = () => {
      chartInstance?.setOption(getChartOption(maskImg), { notMerge: true })
    }
    if (maskImg.complete) {
      applyOption()
    } else {
      maskImg.onload = applyOption
    }
  } else {
    initChart()
  }
}, { deep: true })
</script>

<style scoped>
.chart-container {
  width: 100%;
  height: 420px;
}
</style>
