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
  const s = 320
  const canvas = document.createElement('canvas')
  canvas.width = s
  canvas.height = s
  const ctx = canvas.getContext('2d')!

  ctx.fillStyle = '#ffffff'

  // ── Cap Board (mortarboard) ──
  // Wide trapezoid at top: narrower at top, wider at bottom
  const bx = 32, by = 12, bw = s - 64, bh = 64
  ctx.beginPath()
  ctx.moveTo(bx, by + bh)              // bottom-left (32, 76)
  ctx.lineTo(bx + 20, by)              // top-left (52, 12)
  ctx.lineTo(bx + bw - 20, by)         // top-right (268, 12)
  ctx.lineTo(bx + bw, by + bh)         // bottom-right (288, 76)
  ctx.closePath()
  ctx.fill()

  // ── Board Rim (帽岩) ──
  // Prominent horizontal line across the board bottom
  ctx.beginPath()
  ctx.moveTo(bx + 6, by + bh - 8)      // (38, 68)
  ctx.lineTo(bx + bw - 6, by + bh - 8) // (282, 68)
  ctx.lineWidth = 4
  ctx.strokeStyle = '#ffffff'
  ctx.stroke()

  // ── Cap Button ──
  // Prominent circle at center top of board
  ctx.beginPath()
  ctx.arc(s / 2, by - 4, 10, 0, Math.PI * 2)  // (160, 8), r=10
  ctx.fill()

  // ── Cylinder Body ──
  // Vertical cylinder from board bottom down to y=240
  // Slight curves on sides for 3D cylindrical appearance
  const cylTop = by + bh              // 76
  const cylBottom = 240
  const cylLeft = 72
  const cylRight = s - 72             // 248
  ctx.beginPath()
  ctx.moveTo(cylLeft, cylTop)
  // Left side: slight outward curve then back in
  ctx.bezierCurveTo(cylLeft - 8, cylTop + 60, cylLeft - 8, cylBottom - 30, cylLeft, cylBottom)
  // Bottom curve (rounded base)
  ctx.quadraticCurveTo(s / 2, cylBottom + 12, cylRight, cylBottom)
  // Right side: slight outward curve then back in
  ctx.bezierCurveTo(cylRight + 8, cylBottom - 30, cylRight + 8, cylTop + 60, cylRight, cylTop)
  ctx.closePath()
  ctx.fill()

  // ── Cap Seam Line ──
  // Vertical center line from board bottom through cylinder
  ctx.beginPath()
  ctx.moveTo(s / 2, cylTop)
  ctx.lineTo(s / 2, cylBottom - 8)
  ctx.lineWidth = 3
  ctx.strokeStyle = '#ffffff'
  ctx.stroke()

  // ── Tassel ──
  // Curving from button area to right edge of cylinder
  const tasselStartX = s / 2 + 10     // 170
  const tasselStartY = by + 24        // 36
  ctx.beginPath()
  ctx.moveTo(tasselStartX, tasselStartY)
  ctx.quadraticCurveTo(s - 36, by + 56, cylRight, cylTop + 24)
  ctx.lineWidth = 6
  ctx.strokeStyle = '#ffffff'
  ctx.stroke()

  // ── Tassel Knot ──
  ctx.beginPath()
  ctx.arc(cylRight, cylTop + 24, 12, 0, Math.PI * 2)  // (248, 100), r=12
  ctx.fill()

  // ── Tassel Fringe ──
  // 4 short vertical lines hanging below knot
  for (let fi = -1; fi <= 2; fi++) {
    const fx = cylRight + (fi - 0.5) * 9
    ctx.beginPath()
    ctx.moveTo(fx, cylTop + 36)       // 112
    ctx.lineTo(fx - 2, cylTop + 60)   // 136
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
