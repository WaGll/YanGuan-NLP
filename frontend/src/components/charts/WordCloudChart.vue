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

function createPandaMask(): HTMLImageElement {
  const s = 320
  const canvas = document.createElement('canvas')
  canvas.width = s
  canvas.height = s
  const ctx = canvas.getContext('2d')!

  ctx.fillStyle = '#ffffff'

  // ── Panda Head ──
  // Large round head, slightly wider than tall for a cute panda look
  const headCX = s / 2       // 160
  const headCY = 172
  const headRX = 130          // wider horizontally
  const headRY = 120          // slightly compressed vertically
  ctx.beginPath()
  ctx.ellipse(headCX, headCY, headRX, headRY, 0, 0, Math.PI * 2)
  ctx.fill()

  // ── Left Ear ──
  // Round ear at upper-left of head
  const earRadius = 38
  const leftEarCX = headCX - headRX * 0.62   // ~79
  const leftEarCY = headCY - headRY * 0.85    // ~70
  ctx.beginPath()
  ctx.arc(leftEarCX, leftEarCY, earRadius, 0, Math.PI * 2)
  ctx.fill()

  // ── Right Ear ──
  // Round ear at upper-right of head
  const rightEarCX = headCX + headRX * 0.62  // ~241
  const rightEarCY = headCY - headRY * 0.85   // ~70
  ctx.beginPath()
  ctx.arc(rightEarCX, rightEarCY, earRadius, 0, Math.PI * 2)
  ctx.fill()

  // ── Eye Patches ──
  // Dark oval eye patches — these are part of panda silhouette
  // Left eye patch
  const eyePatchRX = 34
  const eyePatchRY = 38
  const leftEyeCX = headCX - headRX * 0.35   // ~115
  const leftEyeCY = headCY - 8                 // ~164
  ctx.beginPath()
  ctx.ellipse(leftEyeCX, leftEyeCY, eyePatchRX, eyePatchRY, -0.25, 0, Math.PI * 2)
  ctx.fill()

  // Right eye patch
  const rightEyeCX = headCX + headRX * 0.35  // ~205
  const rightEyeCY = headCY - 8                // ~164
  ctx.beginPath()
  ctx.ellipse(rightEyeCX, rightEyeCY, eyePatchRX, eyePatchRY, 0.25, 0, Math.PI * 2)
  ctx.fill()

  // ── Nose ──
  // Small triangular nose
  const noseCX = headCX
  const noseCY = headCY + 18
  ctx.beginPath()
  ctx.moveTo(noseCX - 14, noseCY - 6)
  ctx.lineTo(noseCX + 14, noseCY - 6)
  ctx.lineTo(noseCX, noseCY + 12)
  ctx.closePath()
  ctx.fill()

  // ── Mouth ──
  // Inverted Y shape below nose
  ctx.beginPath()
  ctx.moveTo(noseCX, noseCY + 12)
  ctx.lineTo(noseCX, noseCY + 36)
  ctx.lineWidth = 4
  ctx.strokeStyle = '#ffffff'
  ctx.stroke()
  // Mouth curves
  ctx.beginPath()
  ctx.moveTo(noseCX - 20, noseCY + 30)
  ctx.quadraticCurveTo(noseCX - 6, noseCY + 40, noseCX, noseCY + 36)
  ctx.lineWidth = 4
  ctx.strokeStyle = '#ffffff'
  ctx.stroke()
  ctx.beginPath()
  ctx.moveTo(noseCX + 20, noseCY + 30)
  ctx.quadraticCurveTo(noseCX + 6, noseCY + 40, noseCX, noseCY + 36)
  ctx.lineWidth = 4
  ctx.strokeStyle = '#ffffff'
  ctx.stroke()

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
  const maskImg = createPandaMask()
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
    const maskImg = createPandaMask()
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
