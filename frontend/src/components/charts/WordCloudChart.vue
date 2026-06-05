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

  // Cap board (trapezoid at top) — wider and sharper
  const bx = 32, by = 28, bw = s - 64, bh = 44
  ctx.beginPath()
  ctx.moveTo(bx, by + bh)
  ctx.lineTo(bx + 16, by)
  ctx.lineTo(bx + bw - 16, by)
  ctx.lineTo(bx + bw, by + bh)
  ctx.closePath()
  ctx.fill()

  // Cap rim line (horizontal detail line near bottom of board)
  ctx.beginPath()
  ctx.moveTo(bx + 6, by + bh - 8)
  ctx.lineTo(bx + bw - 6, by + bh - 8)
  ctx.lineWidth = 3
  ctx.strokeStyle = '#ffffff'
  ctx.stroke()

  // Cap button (center top of board)
  ctx.beginPath()
  ctx.arc(s / 2, by - 2, 7, 0, Math.PI * 2)
  ctx.fill()

  // Skull cap (rounded dome below)
  ctx.beginPath()
  ctx.moveTo(bx + 30, by + bh)
  ctx.quadraticCurveTo(s / 2, s - 36, bx + bw - 30, by + bh)
  ctx.closePath()
  ctx.fill()

  // Skull cap seam line (vertical detail)
  ctx.beginPath()
  ctx.moveTo(s / 2, by + bh)
  ctx.lineTo(s / 2, s - 20)
  ctx.lineWidth = 2
  ctx.strokeStyle = '#ffffff'
  ctx.stroke()

  // Tassel line
  ctx.beginPath()
  ctx.moveTo(bx + bw - 30, by + bh - 4)
  ctx.quadraticCurveTo(bx + bw - 6, by + 72, bx + bw - 20, by + 96)
  ctx.lineWidth = 5
  ctx.strokeStyle = '#ffffff'
  ctx.stroke()

  // Tassel knot
  ctx.beginPath()
  ctx.arc(bx + bw - 20, by + 96, 10, 0, Math.PI * 2)
  ctx.fill()

  // Tassel fringe (3 short lines below knot)
  for (let fi = -1; fi <= 1; fi++) {
    ctx.beginPath()
    ctx.moveTo(bx + bw - 20 + fi * 6, by + 106)
    ctx.lineTo(bx + bw - 20 + fi * 8, by + 124)
    ctx.lineWidth = 3
    ctx.strokeStyle = '#ffffff'
    ctx.stroke()
  }

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
      sizeRange: [12, 48],
      rotationRange: [-45, 45],
      rotationStep: 45,
      gridSize: 4,
      drawOutOfBound: false,
      layoutAnimation: true,
      shape: 'circle',
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
