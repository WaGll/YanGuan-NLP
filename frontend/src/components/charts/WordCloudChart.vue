<template>
  <div class="wc-root" :class="{ 'wc-root--dark': isDark }">
    <div class="wc-bar" v-if="showExport">
      <button class="wc-btn" @click="exportPNG('png')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
        PNG 4K
      </button>
      <button class="wc-btn" @click="exportPNG('svg')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 3 21 3 21 8"/><line x1="4" y1="20" x2="21" y2="3"/></svg>
        SVG
      </button>
      <button class="wc-btn" @click="toggleDark">🌓</button>
      <span class="wc-stat">{{ placedCount }} words</span>
    </div>
    <div ref="wrapRef" class="wc-wrap">
      <canvas ref="canvasRef" class="wc-canvas" @click="onClick"></canvas>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'

// ── Types ──
export interface WordCloudItem { name: string; value: number }
interface Placed { text: string; x: number; y: number; w: number; h: number; fs: number }
interface Pool { data: Int32Array; cursor: number; len: number }

const R = 2000  // internal render size
const E = 4000  // export size
const MW = R / 2 // mask resolution (1000)
const MH = R / 2

const props = withDefaults(defineProps<{
  data: WordCloudItem[]
  maxWords?: number
  darkMode?: boolean
  showExport?: boolean
}>(), { maxWords: 1000, darkMode: undefined, showExport: true })

const emit = defineEmits<{ 'word-click': [item: WordCloudItem] }>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const wrapRef = ref<HTMLElement | null>(null)
const darkOverride = ref(false)
const placedCount = ref(0)
let placed: Placed[] = []
let maskBin: Uint8Array | null = null
let distMap: Uint16Array | null = null
let occGrid: Uint8Array | null = null
const GRID = 2; let GW = 0; let GH = 0

const prefersDark = ref(false)
let darkMQL: MediaQueryList | null = null
const isDark = computed(() => props.darkMode ?? (darkOverride.value || prefersDark.value))
function toggleDark() { darkOverride.value = !darkOverride.value; nextTick(() => renderAll()) }

// ── Colors ──
const L = {
  bg: '#fafaf7', bamboo: 'rgba(140,155,130,0.15)',
  high: ['#1a1a2e','#16213e','#0f3460','#1a1a2e','#1c1c30'],
  mid:  ['#4a4a6a','#3a3a55','#4e4e6a','#444460','#3d3d5c'],
  low:  ['#707088','#787890','#6a6a85','#808098','#686878'],
}
const D = {
  bg: '#0d0d12', bamboo: 'rgba(55,65,50,0.18)',
  high: ['#f0f0f8','#e8e8f0','#f8f8ff','#e0e0ee','#ececf4'],
  mid:  ['#b0b0c4','#a0a0b8','#b8b8cc','#a8a8c0','#9898b0'],
  low:  ['#707088','#686880','#787890','#606078','#808098'],
}
function C() { return isDark.value ? D : L }

// ── Mask & distance transform ──
function buildMask(): void {
  const c = document.createElement('canvas'); c.width = R; c.height = R
  const ctx = c.getContext('2d')!; ctx.fillStyle = '#fff'

  // Panda head
  const hx = R/2, hy = 1100, hrx = 830, hry = 780
  ctx.beginPath(); ctx.ellipse(hx, hy, hrx, hry, 0, 0, Math.PI*2); ctx.fill()
  // Ears
  ctx.beginPath(); ctx.arc(580, 480, 250, 0, Math.PI*2); ctx.fill()
  ctx.beginPath(); ctx.arc(1420, 480, 250, 0, Math.PI*2); ctx.fill()
  // Eye rings (dark oval patches around eyes — most recognizable panda feature)
  // Made larger (rx=140,ry=170) to accommodate more high-frequency words
  ctx.save()
  ctx.translate(720, 880); ctx.rotate(-0.15)
  ctx.beginPath(); ctx.ellipse(0, 0, 140, 170, 0, 0, Math.PI*2); ctx.fill()
  ctx.restore()
  ctx.save()
  ctx.translate(1280, 880); ctx.rotate(0.15)
  ctx.beginPath(); ctx.ellipse(0, 0, 140, 170, 0, 0, Math.PI*2); ctx.fill()
  ctx.restore()

  // Sample to mask grid
  const img = ctx.getImageData(0, 0, R, R).data
  maskBin = new Uint8Array(MW * MH)
  for (let y = 0; y < MH; y++)
    for (let x = 0; x < MW; x++)
      maskBin[y * MW + x] = img[((y*2)*R + x*2)*4] > 128 ? 1 : 0
}

function buildDistanceTransform(): void {
  if (!maskBin) return
  distMap = new Uint16Array(MW * MH)
  const INF = 65535
  distMap.fill(INF)

  // Queue for BFS — use a simple array as ring buffer
  const q = new Int32Array(MW * MH * 2)
  let head = 0, tail = 0

  // Seed: mask pixels adjacent to non-mask (or canvas edge)
  for (let y = 0; y < MH; y++) {
    for (let x = 0; x < MW; x++) {
      if (!maskBin[y * MW + x]) continue
      let isEdge = false
      for (const [dx, dy] of [[-1,0],[1,0],[0,-1],[0,1]]) {
        const nx = x + dx, ny = y + dy
        if (nx < 0 || nx >= MW || ny < 0 || ny >= MH || !maskBin[ny * MW + nx]) {
          isEdge = true; break
        }
      }
      if (isEdge) {
        distMap[y * MW + x] = 0
        q[tail++] = x; q[tail++] = y
      }
    }
  }

  // BFS inward
  while (head < tail) {
    const cx = q[head++], cy = q[head++]
    const nd = distMap[cy * MW + cx] + 1
    for (const [dx, dy] of [[-1,0],[1,0],[0,-1],[0,1]]) {
      const nx = cx + dx, ny = cy + dy
      if (nx >= 0 && nx < MW && ny >= 0 && ny < MH && maskBin[ny * MW + nx] && distMap[ny * MW + nx] > nd) {
        distMap[ny * MW + nx] = nd
        q[tail++] = nx; q[tail++] = ny
      }
    }
  }
}

// ── Region helpers ──
function isEarRegion(mx: number, my: number): boolean {
  const dx1 = mx - 290, dy1 = my - 240; if (dx1*dx1 + dy1*dy1 <= 120*120) return true
  const dx2 = mx - 710, dy2 = my - 240; if (dx2*dx2 + dy2*dy2 <= 120*120) return true
  return false
}

// Eye ring region check in mask coords (1000x1000)
// Eye rings are tilted ellipses at (360,440) and (640,440), rx=70 ry=85
function isEyeRingRegion(mx: number, my: number): boolean {
  const COS = Math.cos(-0.15), SIN = Math.sin(-0.15)
  // Left eye ring
  let dx = mx - 360, dy = my - 440
  let rx = dx * COS - dy * SIN, ry = dx * SIN + dy * COS
  if ((rx*rx)/(70*70) + (ry*ry)/(85*85) <= 1) return true
  // Right eye ring
  dx = mx - 640; dy = my - 440
  rx = dx * COS - dy * SIN; ry = dx * SIN + dy * COS
  if ((rx*rx)/(70*70) + (ry*ry)/(85*85) <= 1) return true
  return false
}

function buildPools(): { ear: Pool; eyeRing: Pool; center: Pool; mid: Pool; edge: Pool } {
  if (!maskBin || !distMap) throw new Error('mask not built')

  const dists: number[] = []
  for (let i = 0; i < MW * MH; i++) {
    if (maskBin[i] && distMap[i] < 65535) dists.push(distMap[i])
  }
  dists.sort((a, b) => a - b)
  const p25 = dists[Math.floor(dists.length * 0.7)] ?? 0
  const p40 = dists[Math.floor(dists.length * 0.3)] ?? 0

  const total = dists.length
  const eyeRingArr = new Int32Array(total * 2)
  const earArr = new Int32Array(total * 2)
  const centerArr = new Int32Array(total * 2)
  const midArr = new Int32Array(total * 2)
  const edgeArr = new Int32Array(total * 2)
  let eyeRingN = 0, earN = 0, centerN = 0, midN = 0, edgeN = 0

  for (let y = 0; y < MH; y++) {
    for (let x = 0; x < MW; x++) {
      const idx = y * MW + x
      if (!maskBin[idx] || distMap[idx] >= 65535) continue
      const d = distMap[idx]
      const rx = x * 2, ry = y * 2

      if (isEarRegion(x, y)) {
        earArr[earN * 2] = rx; earArr[earN * 2 + 1] = ry; earN++
      } else if (isEyeRingRegion(x, y)) {
        eyeRingArr[eyeRingN * 2] = rx; eyeRingArr[eyeRingN * 2 + 1] = ry; eyeRingN++
      } else if (d >= p25) {
        centerArr[centerN * 2] = rx; centerArr[centerN * 2 + 1] = ry; centerN++
      } else if (d >= p40) {
        midArr[midN * 2] = rx; midArr[midN * 2 + 1] = ry; midN++
      } else {
        edgeArr[edgeN * 2] = rx; edgeArr[edgeN * 2 + 1] = ry; edgeN++
      }
    }
  }

  function shuffle(arr: Int32Array, n: number) {
    for (let i = n - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1))
      const ax = arr[i * 2], ay = arr[i * 2 + 1]
      arr[i * 2] = arr[j * 2]; arr[i * 2 + 1] = arr[j * 2 + 1]
      arr[j * 2] = ax; arr[j * 2 + 1] = ay
    }
  }
  shuffle(earArr, earN); shuffle(eyeRingArr, eyeRingN)
  shuffle(centerArr, centerN); shuffle(midArr, midN); shuffle(edgeArr, edgeN)

  return {
    ear:     { data: earArr, cursor: 0, len: earN },
    eyeRing: { data: eyeRingArr, cursor: 0, len: eyeRingN },
    center:  { data: centerArr, cursor: 0, len: centerN },
    mid:     { data: midArr, cursor: 0, len: midN },
    edge:    { data: edgeArr, cursor: 0, len: edgeN },
  }
}

// ── Occupancy grid ──
function initOcc() { GW = Math.ceil(R / GRID); GH = Math.ceil(R / GRID); occGrid = new Uint8Array(GW * GH) }
function markOcc(x: number, y: number, w: number, h: number) {
  if (!occGrid) return
  const m = 0, gx1 = Math.max(0, (x - m) / GRID | 0), gy1 = Math.max(0, (y - m) / GRID | 0)
  const gx2 = Math.min(GW, (x + w + m) / GRID + 1 | 0), gy2 = Math.min(GH, (y + h + m) / GRID + 1 | 0)
  for (let gy = gy1; gy < gy2; gy++) for (let gx = gx1; gx < gx2; gx++) occGrid[gy * GW + gx] = 1
}
function isOcc(x: number, y: number, w: number, h: number): boolean {
  if (!occGrid) return false
  const m = 0, gx1 = Math.max(0, (x - m) / GRID | 0), gy1 = Math.max(0, (y - m) / GRID | 0)
  const gx2 = Math.min(GW, (x + w + m) / GRID + 1 | 0), gy2 = Math.min(GH, (y + h + m) / GRID + 1 | 0)
  for (let gy = gy1; gy < gy2; gy++) for (let gx = gx1; gx < gx2; gx++) if (occGrid[gy * GW + gx]) return true
  return false
}

// ── Word placement using pools ──
function placeFromPool(
  ctx: CanvasRenderingContext2D, words: Array<{name:string;value:number}>,
  pool: Pool, fsMin: number, fsMax: number, fw: number, colors: string[], maxTry: number,
  allowShrink: boolean = true
): number {
  if (words.length === 0 || pool.len === 0) return 0
  pool.cursor = 0
  const maxVal = words[0]?.value ?? 1; const minVal = words[words.length-1]?.value ?? 1
  let count = 0

  const sizes = words.map(w => {
    const norm = maxVal > minVal ? (w.value - minVal) / (maxVal - minVal) : 0.5
    return fsMin + norm * (fsMax - fsMin)
  })

  const measCanvas = document.createElement('canvas')
  const measCtx = measCanvas.getContext('2d')!

  for (let wi = 0; wi < words.length; wi++) {
    const targetFS = sizes[wi]

    // Try target size first, then progressively shrink down to 50%
    const shrinkSteps = allowShrink ? [1.0, 0.85, 0.7, 0.55] : [1.0]
    let placed_ok = false; let px = 0; let py = 0; let finalFS = targetFS

    for (const shrink of shrinkSteps) {
      const fontSize = Math.max(fsMin * 0.5, targetFS * shrink)
      const fontStr = `${fw} ${fontSize}px "PingFang SC","Microsoft YaHei","Noto Sans SC",sans-serif`
      measCtx.font = fontStr
      const tm = measCtx.measureText(words[wi].name)
      const tw = tm.width + 1; const th = fontSize * 1.15

      // Pick a random starting point in the pool for better distribution
      const startAt = pool.cursor > 0 ? pool.cursor : Math.floor(Math.random() * pool.len)
      pool.cursor = startAt

      for (let attempt = 0; attempt < maxTry; attempt++) {
        if (pool.cursor >= pool.len) pool.cursor = 0
        const ci = pool.cursor++
        const sx = pool.data[ci * 2], sy = pool.data[ci * 2 + 1]

        if (sx + tw > R - 3 || sy + th > R - 3 || sx < 3 || sy < 3) continue
        if (isOcc(sx, sy, tw, th)) continue
        placed_ok = true; px = sx; py = sy; finalFS = fontSize; break
      }
      if (placed_ok) break
    }

    if (placed_ok) {
      const fontStr = `${fw} ${finalFS}px "PingFang SC","Microsoft YaHei","Noto Sans SC",sans-serif`
      const color = colors[Math.floor(Math.random() * colors.length)]
      ctx.fillStyle = color
      ctx.font = fontStr
      ctx.fillText(words[wi].name, px, py + finalFS * 0.85)
      markOcc(px, py, measCtx.measureText(words[wi].name).width + 1, finalFS * 1.15)
      placed.push({ text: words[wi].name, x: px, y: py, w: measCtx.measureText(words[wi].name).width + 1, h: finalFS * 1.15, fs: finalFS })
      count++
    }
  }
  return count
}

// ── Bamboo leaves ──
function drawBamboo(ctx: CanvasRenderingContext2D) {
  const c = C()
  const leaves = [[160,240,0.6,1.0],[1840,200,-0.5,0.9],[120,800,0.3,0.7],[1880,760,-0.7,0.8],
    [300,1500,0.8,0.9],[1720,1480,-0.4,0.75],[200,1850,1.0,0.85],[1840,1780,-0.9,0.7],
    [380,1920,0.5,0.6],[1620,1900,-0.6,0.65]]
  ctx.save()
  for (const [cx,cy,ang,sc] of leaves) {
    const len = 180*sc, wid = 28*sc
    ctx.save(); ctx.translate(cx, cy); ctx.rotate(ang)
    ctx.beginPath(); ctx.moveTo(0,0)
    ctx.bezierCurveTo(wid*0.4,-len*0.3,wid,-len*0.6,0,-len)
    ctx.bezierCurveTo(-wid,-len*0.6,-wid*0.4,-len*0.3,0,0)
    ctx.fillStyle = c.bamboo; ctx.fill()
    ctx.beginPath(); ctx.moveTo(0,-8); ctx.lineTo(0,-len+20)
    ctx.strokeStyle = c.bamboo; ctx.lineWidth = 2.4*sc; ctx.stroke()
    ctx.restore()
  }
  ctx.restore()
}

// ── Main render ──
function renderAll() {
  const canvas = canvasRef.value
  if (!canvas || props.data.length === 0) return

  canvas.width = R; canvas.height = R
  const ctx = canvas.getContext('2d')!
  const c = C()
  ctx.clearRect(0, 0, R, R)
  if (c.bg !== 'transparent') { ctx.fillStyle = c.bg; ctx.fillRect(0, 0, R, R) }

  // Build mask + distance transform
  buildMask()
  buildDistanceTransform()

  // Build position pools
  const pools = buildPools()

  // Init occupancy grid
  initOcc()
  placed = []

  // Draw bamboo background
  drawBamboo(ctx)

  // Prepare word list — pad to >= maxWords
  const sorted = [...props.data].sort((a, b) => b.value - a.value)
  const N = Math.max(props.maxWords, 1500)
  const words: Array<{name:string;value:number}> = sorted.map(w => ({...w}))
  let ri = Math.floor(sorted.length * 0.6)
  while (words.length < N) {
    if (ri >= sorted.length) ri = Math.floor(sorted.length * 0.4)
    words.push({ name: sorted[ri].name, value: sorted[ri].value * (0.3 + Math.random() * 0.6) })
    ri++
  }
  const total = words.length
  const eyeCut = Math.floor(total * 0.04)    // top 4% → eye rings
  const earCut = Math.floor(total * 0.12)    // next 8% → ears
  const centerCut = Math.floor(total * 0.35) // next 23% → head center
  const midCut = Math.floor(total * 0.70)    // next 35% → face/body

  const eyeRingWords = words.slice(0, eyeCut)
  const earWords = words.slice(eyeCut, earCut)
  const centerWords = words.slice(earCut, centerCut)
  const midWords = words.slice(centerCut, midCut)
  const edgeWords = words.slice(midCut)

  // ── Placement: edge → mid → center → ears → eye rings ──
  let totalPlaced = 0
  totalPlaced += placeFromPool(ctx, edgeWords, pools.edge, 6, 16, 400, c.low, 2500, true)
  totalPlaced += placeFromPool(ctx, midWords, pools.mid, 14, 32, 500, c.mid, 2000, true)
  totalPlaced += placeFromPool(ctx, centerWords, pools.center, 28, 64, 700, c.high, 2000, true)
  totalPlaced += placeFromPool(ctx, earWords, pools.ear, 56, 160, 700, c.high, 1000, true)
  totalPlaced += placeFromPool(ctx, eyeRingWords, pools.eyeRing, 72, 200, 700, ['#0a0a1a','#0d0d22','#08081c'], 1000, false)

  // Light gap-fill: only edge pool for outline density
  if (pools.edge.len > 0) {
    totalPlaced += placeFromPool(ctx, words.slice(0, Math.floor(total * 0.3)), pools.edge, 5, 11, 400, c.low, 200, true)
  }

  placedCount.value = placed.length
}

// ── Click ──
function onClick(e: MouseEvent) {
  const canvas = canvasRef.value
  if (!canvas || placed.length === 0) return
  const rect = canvas.getBoundingClientRect()
  const sx = R / rect.width; const sy = R / rect.height
  const cx = (e.clientX - rect.left) * sx; const cy = (e.clientY - rect.top) * sy
  for (const pw of placed) {
    if (cx >= pw.x && cx <= pw.x + pw.w && cy >= pw.y && cy <= pw.y + pw.h) {
      const m = props.data.find(d => d.name === pw.text)
      if (m) emit('word-click', m)
      return
    }
  }
}

// ── Export ──
function exportPNG(fmt: 'png' | 'svg') {
  const canvas = canvasRef.value
  if (!canvas) return
  if (fmt === 'png') {
    const s = E / R; const ec = document.createElement('canvas')
    ec.width = E; ec.height = E; const ectx = ec.getContext('2d')!
    ectx.scale(s, s); ectx.drawImage(canvas, 0, 0)
    const a = document.createElement('a'); a.download = 'panda-wordcloud-4k.png'
    a.href = ec.toDataURL('image/png'); a.click()
  } else {
    const c = C()
    let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${E}" height="${E}" viewBox="0 0 ${R} ${R}">`
    if (c.bg !== 'transparent') svg += `<rect width="${R}" height="${R}" fill="${c.bg}"/>`
    for (const pw of placed) {
      svg += `<text x="${pw.x}" y="${pw.y + pw.fs * 0.85}" font-size="${pw.fs}" font-family="PingFang SC,Microsoft YaHei,Noto Sans SC,sans-serif" fill="${c.high[0]}" font-weight="700">${escapeXml(pw.text)}</text>`
    }
    svg += '</svg>'
    const b = new Blob([svg], { type: 'image/svg+xml' })
    const a = document.createElement('a'); a.download = 'panda-wordcloud-4k.svg'
    a.href = URL.createObjectURL(b); a.click(); URL.revokeObjectURL(a.href)
  }
}
function escapeXml(s: string) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;') }

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
.wc-bar { position: absolute; top: 10px; right: 12px; z-index: 10; display: flex; align-items: center; gap: 6px; opacity: 0; transition: opacity 0.2s; }
.wc-root:hover .wc-bar { opacity: 1; }
.wc-btn { display: inline-flex; align-items: center; gap: 5px; height: 30px; padding: 0 10px; border: 1px solid rgba(0,0,0,0.08); border-radius: 8px; background: rgba(255,255,255,0.88); backdrop-filter: blur(8px); color: #475569; font-size: 11px; font-weight: 500; font-family: inherit; cursor: pointer; transition: all 0.15s; }
.wc-btn:hover { background: #fff; color: #1e293b; border-color: rgba(0,0,0,0.15); }
.wc-root--dark .wc-btn { background: rgba(30,30,40,0.88); border-color: rgba(255,255,255,0.08); color: #a0a0b0; }
.wc-root--dark .wc-btn:hover { background: rgba(40,40,55,0.95); color: #e0e0e0; }
.wc-stat { font-size: 10px; color: #94a3b8; margin-left: 4px; font-variant-numeric: tabular-nums; }
.wc-root--dark .wc-stat { color: #606070; }
.wc-wrap { width: 100%; aspect-ratio: 1 / 1; max-height: 560px; }
.wc-canvas { width: 100%; height: 100%; display: block; object-fit: contain; }
</style>
