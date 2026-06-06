<template>
  <div class="wc-wrapper" :class="{ 'wc-wrapper--dark': isDark }">
    <div class="wc-toolbar" v-if="showExport">
      <button class="wc-btn" @click="exportPNG" title="导出 4K PNG">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
        Export 4K
      </button>
      <button class="wc-btn" @click="toggleDark" title="切换深色模式">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
      </button>
    </div>
    <div ref="containerRef" class="wc-canvas-wrap">
      <canvas ref="canvasRef" class="wc-canvas" @click="handleClick"></canvas>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'

// ── Types ──
export interface WordCloudItem {
  name: string
  value: number
}

interface PlacedWord {
  text: string
  x: number
  y: number
  w: number
  h: number
  fontSize: number
  tier: 'high' | 'mid' | 'low'
}

interface Region {
  name: string
  contains(x: number, y: number): boolean
}

const props = withDefaults(defineProps<{
  data: WordCloudItem[]
  maxWords?: number
  darkMode?: boolean
  showExport?: boolean
}>(), {
  maxWords: 120,
  darkMode: undefined,
  showExport: true,
})

const emit = defineEmits<{
  'word-click': [item: WordCloudItem]
}>()

// ── State ──
const canvasRef = ref<HTMLCanvasElement | null>(null)
const containerRef = ref<HTMLElement | null>(null)
const darkOverride = ref(false)
const placedWords = ref<PlacedWord[]>([])
const INTERNAL_SIZE = 1024

const prefersDark = ref(false)
let darkMQL: MediaQueryList | null = null

const isDark = computed(() => {
  if (props.darkMode !== undefined) return props.darkMode
  if (darkOverride.value) return true
  return prefersDark.value
})

function toggleDark() {
  darkOverride.value = !darkOverride.value
  nextTick(() => render())
}

// ── Ink-wash color palette ──
interface ColorScheme {
  bg: string
  highFreq: string[]
  midFreq: string[]
  lowFreq: string[]
  bambooStroke: string
  bambooFill: string
}

const lightColors: ColorScheme = {
  bg: 'transparent',
  highFreq: ['#1a1a2e', '#16213e', '#0f3460', '#1a1a2e', '#2d2d44'],
  midFreq: ['#3d3d5c', '#4a4a6a', '#5c5c7a', '#3a3a52', '#4e4e68'],
  lowFreq: ['#7a7a95', '#8a8aa5', '#9a9ab0', '#85859a', '#9090a5'],
  bambooStroke: 'rgba(140,160,140,0.25)',
  bambooFill: 'rgba(160,185,155,0.12)',
}

const darkColors: ColorScheme = {
  bg: '#0f0f14',
  highFreq: ['#e8e8f0', '#f0f0f8', '#d8d8e8', '#e0e0ee', '#ececf4'],
  midFreq: ['#a0a0b8', '#b0b0c4', '#9898b0', '#a8a8bc', '#b8b8c8'],
  lowFreq: ['#606078', '#686880', '#707088', '#585870', '#787890'],
  bambooStroke: 'rgba(60,75,60,0.35)',
  bambooFill: 'rgba(50,65,50,0.18)',
}

function colors(): ColorScheme {
  return isDark.value ? darkColors : lightColors
}

// ── Region map (熊猫区域) ──
function buildRegions(): { high: Region[]; mid: Region[]; low: Region[] } {
  const S = INTERNAL_SIZE
  const headCX = S / 2        // 512
  const headCY = 560
  const headRX = 410
  const headRY = 380

  // High-frequency regions: ears + eye patches + nose
  const high: Region[] = [
    {
      name: 'leftEar',
      contains: (x, y) => {
        const dx = x - 290, dy = y - 240
        return dx * dx + dy * dy <= 130 * 130
      },
    },
    {
      name: 'rightEar',
      contains: (x, y) => {
        const dx = x - 734, dy = y - 240
        return dx * dx + dy * dy <= 130 * 130
      },
    },
    {
      name: 'leftEye',
      contains: (x, y) => {
        const dx = x - 378, dy = y - 540
        return (dx * dx) / (118 * 118) + (dy * dy) / (135 * 135) <= 1
      },
    },
    {
      name: 'rightEye',
      contains: (x, y) => {
        const dx = x - 646, dy = y - 540
        return (dx * dx) / (118 * 118) + (dy * dy) / (135 * 135) <= 1
      },
    },
    {
      name: 'nose',
      contains: (x, y) => {
        const nx = 512, ny = 620, hw = 50, hh = 40
        if (y < ny - hh || y > ny + hh) return false
        const dx = Math.abs(x - nx)
        const maxW = hw * (1 - (y - (ny - hh)) / (2 * hh))
        return dx <= maxW
      },
    },
  ]

  // Mid-frequency region: panda head body
  const mid: Region[] = [
    {
      name: 'head',
      contains: (x, y) => {
        const dx = (x - headCX) / headRX
        const dy = (y - headCY) / headRY
        return dx * dx + dy * dy <= 1
      },
    },
  ]

  // Low-frequency region: everywhere else on canvas
  const low: Region[] = [
    {
      name: 'background',
      contains: (x, y) => {
        // Outside panda head but inside canvas
        const dx = (x - headCX) / headRX
        const dy = (y - headCY) / headRY
        if (dx * dx + dy * dy <= 1) return false
        return x >= 40 && x <= S - 40 && y >= 40 && y <= S - 40
      },
    },
  ]

  return { high, mid, low }
}

// ── Bamboo leaf drawing ──
function drawBambooLeaves(ctx: CanvasRenderingContext2D) {
  const c = colors()
  const leaves: Array<{ cx: number; cy: number; angle: number; scale: number }> = [
    { cx: 80, cy: 120, angle: 0.6, scale: 1.0 },
    { cx: 920, cy: 100, angle: -0.5, scale: 0.9 },
    { cx: 60, cy: 400, angle: 0.3, scale: 0.7 },
    { cx: 960, cy: 380, angle: -0.7, scale: 0.8 },
    { cx: 150, cy: 750, angle: 0.8, scale: 0.9 },
    { cx: 880, cy: 720, angle: -0.4, scale: 0.75 },
    { cx: 100, cy: 900, angle: 1.0, scale: 0.85 },
    { cx: 940, cy: 880, angle: -0.9, scale: 0.7 },
    { cx: 200, cy: 950, angle: 0.5, scale: 0.6 },
    { cx: 800, cy: 940, angle: -0.6, scale: 0.65 },
  ]

  ctx.save()
  for (const leaf of leaves) {
    const len = 90 * leaf.scale
    const wid = 14 * leaf.scale
    ctx.save()
    ctx.translate(leaf.cx, leaf.cy)
    ctx.rotate(leaf.angle)

    // Leaf body (teardrop)
    ctx.beginPath()
    ctx.moveTo(0, 0)
    ctx.bezierCurveTo(wid * 0.4, -len * 0.3, wid, -len * 0.6, 0, -len)
    ctx.bezierCurveTo(-wid, -len * 0.6, -wid * 0.4, -len * 0.3, 0, 0)
    ctx.fillStyle = c.bambooFill
    ctx.fill()

    // Leaf vein
    ctx.beginPath()
    ctx.moveTo(0, -4)
    ctx.lineTo(0, -len + 10)
    ctx.strokeStyle = c.bambooStroke
    ctx.lineWidth = 1.2 * leaf.scale
    ctx.stroke()

    ctx.restore()
  }
  ctx.restore()
}

// ── Word placement ──
function randomPointInRegion(region: Region, maxTries = 200): { x: number; y: number } | null {
  const S = INTERNAL_SIZE
  for (let i = 0; i < maxTries; i++) {
    const x = 40 + Math.random() * (S - 80)
    const y = 40 + Math.random() * (S - 80)
    if (region.contains(x, y)) return { x, y }
  }
  return null
}

function overlaps(newBox: { x: number; y: number; w: number; h: number }, existing: PlacedWord[]): boolean {
  const pad = 3
  for (const pw of existing) {
    if (
      newBox.x - pad < pw.x + pw.w &&
      newBox.x + newBox.w + pad > pw.x &&
      newBox.y - pad < pw.y + pw.h &&
      newBox.y + newBox.h + pad > pw.y
    ) {
      return true
    }
  }
  return false
}

function assignTier(index: number, total: number): 'high' | 'mid' | 'low' {
  const ratio = index / total
  if (ratio < 0.12) return 'high'
  if (ratio < 0.65) return 'mid'
  return 'low'
}

function fontSizeForTier(tier: 'high' | 'mid' | 'low', value: number, maxVal: number): number {
  const norm = value / maxVal
  switch (tier) {
    case 'high': return 28 + norm * 24   // 28-52
    case 'mid':  return 16 + norm * 16   // 16-32
    case 'low':  return 10 + norm * 10   // 10-20
  }
}

function colorForTier(tier: 'high' | 'mid' | 'low'): string {
  const c = colors()
  const arr = tier === 'high' ? c.highFreq : tier === 'mid' ? c.midFreq : c.lowFreq
  return arr[Math.floor(Math.random() * arr.length)]
}

function render() {
  const canvas = canvasRef.value
  if (!canvas || props.data.length === 0) return

  const S = INTERNAL_SIZE
  canvas.width = S
  canvas.height = S
  const ctx = canvas.getContext('2d')!

  // Clear
  const c = colors()
  ctx.clearRect(0, 0, S, S)
  if (c.bg !== 'transparent') {
    ctx.fillStyle = c.bg
    ctx.fillRect(0, 0, S, S)
  }

  // Sort data by value descending
  const sorted = [...props.data]
    .sort((a, b) => b.value - a.value)
    .slice(0, props.maxWords)

  if (sorted.length === 0) return

  const maxVal = sorted[0]?.value ?? 1
  const regions = buildRegions()
  const placed: PlacedWord[] = []
  const total = sorted.length

  // Phase 1: render bamboo leaves (underneath)
  drawBambooLeaves(ctx)

  // Phase 2: place words
  ctx.textBaseline = 'alphabetic'
  ctx.textAlign = 'left'

  for (let i = 0; i < sorted.length; i++) {
    const word = sorted[i]
    const tier = assignTier(i, total)
    const fontSize = fontSizeForTier(tier, word.value, maxVal)
    const fontColor = colorForTier(tier)
    const fontWeight = tier === 'high' ? '700' : tier === 'mid' ? '500' : '400'

    ctx.font = `${fontWeight} ${fontSize}px "PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif`
    const metrics = ctx.measureText(word.name)
    const tw = metrics.width
    const th = fontSize * 1.2
    const box = { w: tw, h: th }

    // Pick region set for this tier
    const regionSet = tier === 'high' ? regions.high : tier === 'mid' ? regions.mid : regions.low
    if (regionSet.length === 0) continue

    let placed_success = false

    // Try up to 3 random regions from the set
    const shuffledRegions = [...regionSet].sort(() => Math.random() - 0.5).slice(0, 3)
    for (const region of shuffledRegions) {
      const start = randomPointInRegion(region, 150)
      if (!start) continue

      // Archimedean spiral search
      let found = false
      let px = start.x
      let py = start.y
      const a = 2, b = 4
      for (let step = 0; step < 2000; step++) {
        const theta = step * 0.15
        const r = a + b * theta
        px = start.x + r * Math.cos(theta)
        py = start.y + r * Math.sin(theta)

        // Bounds check
        if (px < 10 || py < 10 || px + tw > S - 10 || py + th > S - 10) continue

        // Region containment
        if (!region.contains(px + tw / 2, py + th / 2)) continue

        // Collision check
        const testBox = { x: px, y: py, w: tw, h: th }
        if (!overlaps(testBox, placed)) {
          found = true
          break
        }
      }

      if (found) {
        // Draw
        ctx.fillStyle = fontColor
        ctx.fillText(word.name, px, py + fontSize)

        placed.push({
          text: word.name,
          x: px,
          y: py,
          w: tw,
          h: th,
          fontSize,
          tier,
        })
        placed_success = true
        break
      }
    }

    // Fallback: try any region
    if (!placed_success) {
      const allRegions = [...regions.high, ...regions.mid, ...regions.low]
      const shuffled = [...allRegions].sort(() => Math.random() - 0.5).slice(0, 5)
      for (const region of shuffled) {
        const start = randomPointInRegion(region, 100)
        if (!start) continue

        let found = false
        let px = start.x, py = start.y
        const a = 1, b = 5
        for (let step = 0; step < 3000; step++) {
          const theta = step * 0.12
          const r = a + b * theta
          px = start.x + r * Math.cos(theta)
          py = start.y + r * Math.sin(theta)

          if (px < 10 || py < 10 || px + tw > S - 10 || py + th > S - 10) continue
          if (!region.contains(px + tw / 2, py + th / 2)) continue

          const testBox = { x: px, y: py, w: tw, h: th }
          if (!overlaps(testBox, placed)) {
            found = true
            break
          }
        }

        if (found) {
          ctx.fillStyle = c.lowFreq[0]
          ctx.fillText(word.name, px, py + fontSize)
          placed.push({
            text: word.name,
            x: px,
            y: py,
            w: tw,
            h: th,
            fontSize,
            tier: 'low',
          })
          break
        }
      }
    }
  }

  placedWords.value = placed
}

// ── Click detection ──
function handleClick(e: MouseEvent) {
  const canvas = canvasRef.value
  if (!canvas || placedWords.value.length === 0) return

  const rect = canvas.getBoundingClientRect()
  const scaleX = INTERNAL_SIZE / rect.width
  const scaleY = INTERNAL_SIZE / rect.height
  const cx = (e.clientX - rect.left) * scaleX
  const cy = (e.clientY - rect.top) * scaleY

  for (const pw of placedWords.value) {
    if (cx >= pw.x && cx <= pw.x + pw.w && cy >= pw.y && cy <= pw.y + pw.h) {
      const match = props.data.find((d) => d.name === pw.text)
      if (match) emit('word-click', match)
      return
    }
  }
}

// ── Export ──
function exportPNG() {
  const canvas = canvasRef.value
  if (!canvas) return

  const exportScale = 4  // 1024 * 4 = 4096 (4K)
  const exportCanvas = document.createElement('canvas')
  exportCanvas.width = INTERNAL_SIZE * exportScale
  exportCanvas.height = INTERNAL_SIZE * exportScale
  const ectx = exportCanvas.getContext('2d')!
  ectx.scale(exportScale, exportScale)
  ectx.drawImage(canvas, 0, 0)

  const link = document.createElement('a')
  link.download = 'panda-wordcloud-4k.png'
  link.href = exportCanvas.toDataURL('image/png')
  link.click()
}

defineExpose({ exportPNG, canvasRef })

// ── Lifecycle ──
let resizeObs: ResizeObserver | null = null

onMounted(() => {
  darkMQL = window.matchMedia('(prefers-color-scheme: dark)')
  prefersDark.value = darkMQL.matches
  darkMQL.addEventListener('change', (e) => {
    prefersDark.value = e.matches
    if (props.darkMode === undefined && !darkOverride.value) {
      nextTick(() => render())
    }
  })

  nextTick(() => render())

  if (containerRef.value) {
    resizeObs = new ResizeObserver(() => { /* canvas auto-scales via CSS */ })
    resizeObs.observe(containerRef.value)
  }
})

onUnmounted(() => {
  resizeObs?.disconnect()
  darkMQL?.removeEventListener('change', () => {})
})

watch(() => props.data, () => {
  nextTick(() => render())
}, { deep: true })

watch(() => props.maxWords, () => {
  nextTick(() => render())
})

watch(isDark, () => {
  nextTick(() => render())
})
</script>

<style scoped>
.wc-wrapper {
  position: relative;
  width: 100%;
  border-radius: 16px;
  overflow: hidden;
}

.wc-wrapper--dark {
  background: #0f0f14;
}

.wc-toolbar {
  position: absolute;
  top: 10px;
  right: 12px;
  z-index: 10;
  display: flex;
  gap: 6px;
  opacity: 0;
  transition: opacity 0.2s;
}

.wc-wrapper:hover .wc-toolbar {
  opacity: 1;
}

.wc-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 30px;
  padding: 0 12px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(8px);
  color: #475569;
  font-size: 11px;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.15s;
}

.wc-btn:hover {
  background: #ffffff;
  color: #1e293b;
  border-color: rgba(0, 0, 0, 0.15);
}

.wc-wrapper--dark .wc-btn {
  background: rgba(30, 30, 40, 0.85);
  border-color: rgba(255, 255, 255, 0.08);
  color: #a0a0b0;
}

.wc-wrapper--dark .wc-btn:hover {
  background: rgba(40, 40, 50, 0.95);
  color: #e0e0e0;
}

.wc-canvas-wrap {
  width: 100%;
  aspect-ratio: 1 / 1;
  max-height: 520px;
}

.wc-canvas {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: contain;
}
</style>
