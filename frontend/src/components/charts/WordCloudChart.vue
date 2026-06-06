<template>
  <div class="wc-root" :class="{ 'wc-root--dark': isDark }">
    <!-- Toolbar -->
    <div class="wc-bar" v-if="showExport">
      <button class="wc-btn" @click="exportPNG('png')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
        Export 4K PNG
      </button>
      <button class="wc-btn" @click="exportPNG('svg')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 3 21 3 21 8"/><line x1="4" y1="20" x2="21" y2="3"/><polyline points="21 16 21 21 16 21"/><line x1="15" y1="15" x2="21" y2="21"/><line x1="4" y1="4" x2="9" y2="9"/></svg>
        Export SVG
      </button>
      <button class="wc-btn" @click="toggleDark">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/></svg>
      </button>
      <span class="wc-stat">{{ placedCount }} words</span>
    </div>

    <!-- Canvas -->
    <div ref="wrapRef" class="wc-wrap">
      <canvas ref="canvasRef" class="wc-canvas" @click="onClick"></canvas>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'

// ── Types ──
export interface WordCloudItem { name: string; value: number }

interface Placed { text: string; x: number; y: number; w: number; h: number; fs: number; tier: number }

const props = withDefaults(defineProps<{
  data: WordCloudItem[]
  maxWords?: number
  darkMode?: boolean
  showExport?: boolean
}>(), {
  maxWords: 1000,
  darkMode: undefined,
  showExport: true,
})

const emit = defineEmits<{ 'word-click': [item: WordCloudItem] }>()

// ── Constants ──
const RENDER_SIZE = 2000       // internal render resolution
const EXPORT_SIZE = 4000       // 4K export
const GRID_CELL = 2            // occupancy grid cell size in render pixels
const MARGIN_PX = 1            // margin between words

// ── State ──
const canvasRef = ref<HTMLCanvasElement | null>(null)
const wrapRef = ref<HTMLElement | null>(null)
const darkOverride = ref(false)
const placedCount = ref(0)
let placed: Placed[] = []
let gridW = 0; let gridH = 0; let occGrid: Uint8Array | null = null
let maskIntegral: Float64Array | null = null
let maskW = 0; let maskH = 0
let earEyeMask: Float64Array | null = null  // integral image for ears+eyes region

const prefersDark = ref(false)
let darkMQL: MediaQueryList | null = null
const isDark = computed(() => props.darkMode ?? (darkOverride.value || prefersDark.value))
function toggleDark() { darkOverride.value = !darkOverride.value; nextTick(() => renderAll()) }

// ── Color schemes ──
const LIGHT = {
  bg: '#fafaf7',
  high: ['#1a1a2e', '#16213e', '#0f3460', '#1a1a2e', '#1c1c30'],
  mid:  ['#3d3d5c', '#4a4a6a', '#3a3a55', '#4e4e6a', '#444460'],
  low:  ['#6a6a85', '#787890', '#707080', '#808098', '#686878'],
  bamboo: 'rgba(140,155,130,0.18)',
}

const DARK = {
  bg: '#0d0d12',
  high: ['#f0f0f8', '#e8e8f0', '#f8f8ff', '#e0e0ee', '#ececf4'],
  mid:  ['#b0b0c4', '#a0a0b8', '#b8b8cc', '#a8a8c0', '#9898b0'],
  low:  ['#6a6a80', '#707088', '#606078', '#78788e', '#585870'],
  bamboo: 'rgba(55,65,50,0.22)',
}

function C() { return isDark.value ? DARK : LIGHT }

// ── Mask creation ──
function createMask(): { mask: Uint8Array; w: number; h: number; earEye: Uint8Array } {
  const S = 2000
  const off = document.createElement('canvas')
  off.width = S; off.height = S
  const ctx = off.getContext('2d')!
  ctx.fillStyle = '#ffffff'

  // Panda head (ellipse)
  const hx = S / 2; const hy = 1100; const hrx = 820; const hry = 770
  ctx.beginPath(); ctx.ellipse(hx, hy, hrx, hry, 0, 0, Math.PI * 2); ctx.fill()

  // Ears
  ctx.beginPath(); ctx.arc(580, 480, 250, 0, Math.PI * 2); ctx.fill()
  ctx.beginPath(); ctx.arc(1420, 480, 250, 0, Math.PI * 2); ctx.fill()

  // Sample at 2x2 blocks → 1000×1000 mask
  const MW = S / 2; const MH = S / 2
  const imgData = ctx.getImageData(0, 0, S, S).data
  const mask = new Uint8Array(MW * MH)
  for (let my = 0; my < MH; my++) {
    for (let mx = 0; mx < MW; mx++) {
      const px = mx * 2; const py = my * 2
      const idx = (py * S + px) * 4
      mask[my * MW + mx] = imgData[idx] > 128 ? 1 : 0
    }
  }

  // Ear+eye mask
  ctx.clearRect(0, 0, S, S)
  ctx.fillStyle = '#ffffff'
  // ears
  ctx.beginPath(); ctx.arc(580, 480, 260, 0, Math.PI * 2); ctx.fill()
  ctx.beginPath(); ctx.arc(1420, 480, 260, 0, Math.PI * 2); ctx.fill()
  // eye patches
  ctx.beginPath(); ctx.ellipse(760, 1080, 230, 270, -0.15, 0, Math.PI * 2); ctx.fill()
  ctx.beginPath(); ctx.ellipse(1240, 1080, 230, 270, 0.15, 0, Math.PI * 2); ctx.fill()
  // nose area
  ctx.beginPath()
  ctx.moveTo(940, 1220); ctx.lineTo(1060, 1220)
  ctx.lineTo(1000, 1300); ctx.closePath(); ctx.fill()

  const imgData2 = ctx.getImageData(0, 0, S, S).data
  const earEye = new Uint8Array(MW * MH)
  for (let my = 0; my < MH; my++) {
    for (let mx = 0; mx < MW; mx++) {
      const px = mx * 2; const py = my * 2
      const idx = (py * S + px) * 4
      earEye[my * MW + mx] = imgData2[idx] > 128 ? 1 : 0
    }
  }

  return { mask, w: MW, h: MH, earEye }
}

// Integral image
function buildIntegral(bin: Uint8Array, w: number, h: number): Float64Array {
  const integral = new Float64Array((w + 1) * (h + 1))
  for (let y = 0; y < h; y++) {
    let rowSum = 0
    for (let x = 0; x < w; x++) {
      rowSum += bin[y * w + x]
      const idx = (y + 1) * (w + 1) + (x + 1)
      integral[idx] = integral[y * (w + 1) + (x + 1)] + rowSum
    }
  }
  return integral
}

function rectMaskFill(integral: Float64Array, mw: number, rx: number, ry: number, rw: number, rh: number): number {
  const x1 = Math.max(0, Math.floor(rx / 2)), y1 = Math.max(0, Math.floor(ry / 2))
  const x2 = Math.min(mw, Math.ceil((rx + rw) / 2)), y2 = Math.min(Math.floor(integral.length / (mw + 1)) - 1, Math.ceil((ry + rh) / 2))
  if (x2 <= x1 || y2 <= y1) return 0
  const s = (mw + 1)
  const A = integral[y1 * s + x1], B = integral[y1 * s + x2]
  const C = integral[y2 * s + x1], D = integral[y2 * s + x2]
  const area = (x2 - x1) * (y2 - y1)
  if (area === 0) return 0
  return (D + A - B - C) / area
}

function initOccGrid() {
  gridW = Math.ceil(RENDER_SIZE / GRID_CELL)
  gridH = Math.ceil(RENDER_SIZE / GRID_CELL)
  occGrid = new Uint8Array(gridW * gridH)
}

function markOccupied(x: number, y: number, w: number, h: number) {
  if (!occGrid) return
  const gx1 = Math.max(0, Math.floor((x - MARGIN_PX) / GRID_CELL))
  const gy1 = Math.max(0, Math.floor((y - MARGIN_PX) / GRID_CELL))
  const gx2 = Math.min(gridW, Math.ceil((x + w + MARGIN_PX) / GRID_CELL))
  const gy2 = Math.min(gridH, Math.ceil((y + h + MARGIN_PX) / GRID_CELL))
  for (let gy = gy1; gy < gy2; gy++)
    for (let gx = gx1; gx < gx2; gx++)
      occGrid[gy * gridW + gx] = 1
}

function isOccupied(x: number, y: number, w: number, h: number): boolean {
  if (!occGrid) return false
  const gx1 = Math.max(0, Math.floor((x - MARGIN_PX) / GRID_CELL))
  const gy1 = Math.max(0, Math.floor((y - MARGIN_PX) / GRID_CELL))
  const gx2 = Math.min(gridW, Math.ceil((x + w + MARGIN_PX) / GRID_CELL))
  const gy2 = Math.min(gridH, Math.ceil((y + h + MARGIN_PX) / GRID_CELL))
  for (let gy = gy1; gy < gy2; gy++)
    for (let gx = gx1; gx < gx2; gx++)
      if (occGrid[gy * gridW + gx] !== 0) return true
  return false
}

// ── Word placement ──
function tryPlaceWord(
  text: string, fontSize: number, fontWeight: number, integral: Float64Array, maskW: number,
  startX: number, startY: number, maxSteps: number, minFillRatio: number
): Placed | null {
  // Measure text
  const tmp = document.createElement('canvas').getContext('2d')!
  tmp.font = `${fontWeight} ${fontSize}px "PingFang SC","Microsoft YaHei","Noto Sans SC",sans-serif`
  const tm = tmp.measureText(text)
  const tw = tm.width + 2; const th = fontSize * 1.15

  // Spiral search
  const a = 2; const b = 3
  for (let s = 0; s < maxSteps; s++) {
    const theta = s * 0.12
    const r = a + b * theta
    const px = startX + r * Math.cos(theta)
    const py = startY + r * Math.sin(theta)

    if (px < 5 || py < 5 || px + tw > RENDER_SIZE - 5 || py + th > RENDER_SIZE - 5) continue

    const fill = rectMaskFill(integral, maskW, px, py, tw, th)
    if (fill < minFillRatio) continue

    if (isOccupied(px, py, tw, th)) continue

    markOccupied(px, py, tw, th)
    return { text, x: px, y: py, w: tw, h: th, fs: fontSize, tier: 0 }
  }
  return null
}

// ── Bamboo leaves ──
function drawBamboo(ctx: CanvasRenderingContext2D) {
  const c = C()
  const positions = [
    [160, 240, 0.6, 1.0], [1840, 200, -0.5, 0.9],
    [120, 800, 0.3, 0.7], [1880, 760, -0.7, 0.8],
    [300, 1500, 0.8, 0.9], [1720, 1480, -0.4, 0.75],
    [200, 1850, 1.0, 0.85], [1840, 1780, -0.9, 0.7],
    [380, 1920, 0.5, 0.6], [1620, 1900, -0.6, 0.65],
  ]
  ctx.save()
  for (const [cx, cy, angle, sc] of positions) {
    const len = 180 * sc; const wid = 28 * sc
    ctx.save(); ctx.translate(cx, cy); ctx.rotate(angle)
    ctx.beginPath()
    ctx.moveTo(0, 0)
    ctx.bezierCurveTo(wid * 0.4, -len * 0.3, wid, -len * 0.6, 0, -len)
    ctx.bezierCurveTo(-wid, -len * 0.6, -wid * 0.4, -len * 0.3, 0, 0)
    ctx.fillStyle = c.bamboo; ctx.fill()
    ctx.beginPath(); ctx.moveTo(0, -8); ctx.lineTo(0, -len + 20)
    ctx.strokeStyle = c.bamboo; ctx.lineWidth = 2.4 * sc; ctx.stroke()
    ctx.restore()
  }
  ctx.restore()
}

// ── Main render ──
function renderAll() {
  const canvas = canvasRef.value
  if (!canvas || props.data.length === 0) return

  const S = RENDER_SIZE
  canvas.width = S; canvas.height = S
  const ctx = canvas.getContext('2d')!

  const c = C()
  ctx.clearRect(0, 0, S, S)
  if (c.bg !== 'transparent') { ctx.fillStyle = c.bg; ctx.fillRect(0, 0, S, S) }

  // Build mask
  const { mask, w: MW, h: MH } = createMask()
  const fullIntegral = buildIntegral(mask, MW, MH)
  maskIntegral = fullIntegral; maskW = MW; maskH = MH

  // Ear+eye integral (extracted from the createMask call above — rebuild separately)
  // We rebuild earEye mask by calling createMask again is wasteful; use stored copy
  const { earEye } = createMask()
  const earEyeIntegral = buildIntegral(earEye, MW, MH)
  earEyeMask = earEyeIntegral

  // Init occupancy grid
  initOccGrid()
  placed = []

  // Sort & enrich word list to >= maxWords
  const sorted = [...props.data].sort((a, b) => b.value - a.value)
  const maxVal = sorted[0]?.value ?? 1
  const minVal = sorted[sorted.length - 1]?.value ?? 1

  let words: Array<{ name: string; value: number; repeat: boolean }> = []
  for (const w of sorted) words.push({ name: w.name, value: w.value, repeat: false })

  // Pad with repeats of low-freq words to reach target
  const target = Math.max(props.maxWords, 1000)
  let ri = Math.floor(sorted.length * 0.7)
  while (words.length < target) {
    if (ri >= sorted.length) ri = Math.floor(sorted.length * 0.7)
    const src = sorted[ri]
    words.push({ name: src.name, value: src.value * (0.5 + Math.random() * 0.4), repeat: true })
    ri++
  }
  words = words.slice(0, target)

  const total = words.length
  const highCut = Math.floor(total * 0.12)
  const midCut = Math.floor(total * 0.6)

  // Draw bamboo
  drawBamboo(ctx)

  // ── Pass 1: HIGH-FREQ → ears + eye patches ──
  const highWords = words.slice(0, highCut)
  placeWordsPass(ctx, highWords, 0, earEyeIntegral, MW, {
    fsMin: 60, fsMax: 180, fw: 700,
    maxSteps: 3000, minFill: 0.35, startStrategy: 'region-center',
    colors: c.high,
  })

  // ── Pass 2: MID-FREQ → full mask ──
  const midWords = words.slice(highCut, midCut)
  placeWordsPass(ctx, midWords, highCut, fullIntegral, MW, {
    fsMin: 22, fsMax: 58, fw: 500,
    maxSteps: 2500, minFill: 0.3, startStrategy: 'center',
    colors: c.mid,
  })

  // ── Pass 3: LOW-FREQ + REPEATS → full mask, fill gaps ──
  const lowWords = words.slice(midCut)
  placeWordsPass(ctx, lowWords, midCut, fullIntegral, MW, {
    fsMin: 8, fsMax: 22, fw: 400,
    maxSteps: 4000, minFill: 0.2, startStrategy: 'random-mask',
    colors: c.low,
  })

  placedCount.value = placed.length
}

function placeWordsPass(
  ctx: CanvasRenderingContext2D,
  words: Array<{ name: string; value: number; repeat: boolean }>,
  tierOffset: number,
  integral: Float64Array, MW: number,
  opts: {
    fsMin: number; fsMax: number; fw: number; maxSteps: number;
    minFill: number; startStrategy: string; colors: string[];
  }
) {
  if (words.length === 0) return
  const maxVal = words[0]?.value ?? 1
  const minVal = words[words.length - 1]?.value ?? 1

  for (let i = 0; i < words.length; i++) {
    const w = words[i]
    const norm = maxVal > minVal ? (w.value - minVal) / (maxVal - minVal) : 0.5
    const fontSize = opts.fsMin + norm * (opts.fsMax - opts.fsMin)

    let sx: number, sy: number
    if (opts.startStrategy === 'region-center') {
      // Start from a point within ear/eye mask
      for (let attempt = 0; attempt < 100; attempt++) {
        const tx = 100 + Math.random() * (RENDER_SIZE - 200)
        const ty = 100 + Math.random() * (RENDER_SIZE - 200)
        const fill = rectMaskFill(integral, MW, tx, ty, 2, 2)
        if (fill > 0.5) { sx = tx; sy = ty; break }
      }
      if (!sx!) { sx = RENDER_SIZE / 2; sy = RENDER_SIZE / 2 }
    } else if (opts.startStrategy === 'center') {
      sx = RENDER_SIZE / 2 + (Math.random() - 0.5) * 300
      sy = RENDER_SIZE / 2 + (Math.random() - 0.5) * 300
    } else {
      sx = 100 + Math.random() * (RENDER_SIZE - 200)
      sy = 100 + Math.random() * (RENDER_SIZE - 200)
    }

    const color = opts.colors[Math.floor(Math.random() * opts.colors.length)]
    ctx.fillStyle = color

    // Prepare font for measurement
    const fontStr = `${opts.fw} ${fontSize}px "PingFang SC","Microsoft YaHei","Noto Sans SC",sans-serif`
    ctx.font = fontStr
    const tm = ctx.measureText(w.name)
    const tw = tm.width + 2; const th = fontSize * 1.15

    // Spiral placement
    const a = 2; const b = 3
    let placed_ok = false; let px = 0; let py = 0
    for (let step = 0; step < opts.maxSteps; step++) {
      const theta = step * 0.12
      const r = a + b * theta
      px = sx! + r * Math.cos(theta)
      py = sy! + r * Math.sin(theta)

      if (px < 5 || py < 5 || px + tw > RENDER_SIZE - 5 || py + th > RENDER_SIZE - 5) continue

      const fill = rectMaskFill(integral, MW, px, py, tw, th)
      if (fill < opts.minFill) continue

      if (isOccupied(px, py, tw, th)) continue

      placed_ok = true
      break
    }

    if (placed_ok) {
      markOccupied(px, py, tw, th)
      ctx.fillText(w.name, px, py + fontSize * 0.85)
      placed.push({ text: w.name, x: px, y: py, w: tw, h: th, fs: fontSize, tier: 0 })
    }
  }
}

// ── Click ──
function onClick(e: MouseEvent) {
  const canvas = canvasRef.value
  if (!canvas || placed.length === 0) return
  const rect = canvas.getBoundingClientRect()
  const sx = RENDER_SIZE / rect.width; const sy = RENDER_SIZE / rect.height
  const cx = (e.clientX - rect.left) * sx; const cy = (e.clientY - rect.top) * sy
  for (const pw of placed) {
    if (cx >= pw.x && cx <= pw.x + pw.w && cy >= pw.y && cy <= pw.y + pw.h) {
      const match = props.data.find(d => d.name === pw.text)
      if (match) emit('word-click', match)
      return
    }
  }
}

// ── Export ──
function exportPNG(fmt: 'png' | 'svg') {
  const canvas = canvasRef.value
  if (!canvas) return

  if (fmt === 'png') {
    const scale = EXPORT_SIZE / RENDER_SIZE
    const ec = document.createElement('canvas')
    ec.width = EXPORT_SIZE; ec.height = EXPORT_SIZE
    const ectx = ec.getContext('2d')!
    ectx.scale(scale, scale)
    ectx.drawImage(canvas, 0, 0)
    const link = document.createElement('a')
    link.download = 'panda-wordcloud-4k.png'
    link.href = ec.toDataURL('image/png')
    link.click()
  } else {
    // SVG export — reconstruct from placed words
    const c = C()
    const bg = c.bg === 'transparent' ? 'none' : c.bg
    let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${EXPORT_SIZE}" height="${EXPORT_SIZE}" viewBox="0 0 ${RENDER_SIZE} ${RENDER_SIZE}">`
    if (bg !== 'none') svg += `<rect width="${RENDER_SIZE}" height="${RENDER_SIZE}" fill="${bg}"/>`
    for (const pw of placed) {
      const fill = c.high[0]
      svg += `<text x="${pw.x}" y="${pw.y + pw.fs * 0.85}" font-size="${pw.fs}" font-family="PingFang SC,Microsoft YaHei,Noto Sans SC,sans-serif" fill="${fill}" font-weight="700">${escapeXml(pw.text)}</text>`
    }
    svg += '</svg>'
    const blob = new Blob([svg], { type: 'image/svg+xml' })
    const link = document.createElement('a')
    link.download = 'panda-wordcloud-4k.svg'
    link.href = URL.createObjectURL(blob)
    link.click()
    URL.revokeObjectURL(link.href)
  }
}

function escapeXml(s: string) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;') }

// ── Lifecycle ──
onMounted(() => {
  darkMQL = window.matchMedia('(prefers-color-scheme: dark)')
  prefersDark.value = darkMQL.matches
  darkMQL.addEventListener('change', (e) => {
    prefersDark.value = e.matches
    if (props.darkMode === undefined && !darkOverride.value) nextTick(() => renderAll())
  })
  nextTick(() => renderAll())
})

onUnmounted(() => { darkMQL?.removeEventListener('change', () => {}) })

watch(() => props.data, () => nextTick(() => renderAll()), { deep: true })
watch(() => props.maxWords, () => nextTick(() => renderAll()))
watch(isDark, () => nextTick(() => renderAll()))

defineExpose({ exportPNG, canvasRef, renderAll })
</script>

<style scoped>
.wc-root { position: relative; width: 100%; border-radius: 16px; overflow: hidden; }
.wc-root--dark { background: #0d0d12; }

.wc-bar {
  position: absolute; top: 10px; right: 12px; z-index: 10;
  display: flex; align-items: center; gap: 6px;
  opacity: 0; transition: opacity 0.2s;
}
.wc-root:hover .wc-bar { opacity: 1; }

.wc-btn {
  display: inline-flex; align-items: center; gap: 5px;
  height: 30px; padding: 0 10px;
  border: 1px solid rgba(0,0,0,0.08); border-radius: 8px;
  background: rgba(255,255,255,0.88); backdrop-filter: blur(8px);
  color: #475569; font-size: 11px; font-weight: 500;
  font-family: inherit; cursor: pointer; transition: all 0.15s;
}
.wc-btn:hover { background: #fff; color: #1e293b; border-color: rgba(0,0,0,0.15); }
.wc-root--dark .wc-btn { background: rgba(30,30,40,0.88); border-color: rgba(255,255,255,0.08); color: #a0a0b0; }
.wc-root--dark .wc-btn:hover { background: rgba(40,40,55,0.95); color: #e0e0e0; }

.wc-stat {
  font-size: 10px; color: #94a3b8; margin-left: 4px; font-variant-numeric: tabular-nums;
}
.wc-root--dark .wc-stat { color: #606070; }

.wc-wrap { width: 100%; aspect-ratio: 1 / 1; max-height: 560px; }
.wc-canvas { width: 100%; height: 100%; display: block; object-fit: contain; }
</style>
