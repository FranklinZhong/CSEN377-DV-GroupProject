<template>
  <div class="wc-outer">
    <div class="wc-label-bar">
      <span class="wc-badge">TF-IDF</span>Patient Vocabulary
    </div>
    <canvas ref="cnv" class="wc-canvas" />
    <div v-if="!ready" class="wc-loading" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api/client'

const cnv   = ref<HTMLCanvasElement | null>(null)
const ready = ref(false)

// Logical canvas size — same 1:2 aspect ratio as anatomy-hero.png (887×1774)
// and proportionally close to the SVG render size (max-width:260px → 260×520px)
const W = 240, H = 480

const BP_COLORS: Record<string, string> = {
  brain: '#a78bfa', heart: '#f87171', lung: '#38bdf8',
  liver: '#eab308', stomach: '#fb923c', kidney: '#7c3aed',
  muscle: '#4ade80', blood: '#f43f5e', skin: '#fbbf24',
  vascular: '#06b6d4', immune: '#60a5fa', endocrine: '#d97706',
  eye: '#93c5fd', ear: '#c084fc', reproductive: '#f472b6',
}

onMounted(async () => {
  const el = cnv.value
  if (!el) return

  // ── 1. Fetch TF-IDF words ─────────────────────────────────────────────────
  let tfidf: Record<string, { term: string; score_norm: number }[]> = {}
  try {
    const res = await api.getCorpusNlp()
    if (res.data.success) tfidf = res.data.data.tfidf
  } catch { return }

  // ── 2. HiDPI canvas ───────────────────────────────────────────────────────
  const dpr = window.devicePixelRatio || 1
  el.width  = W * dpr
  el.height = H * dpr
  el.style.width  = W + 'px'
  el.style.height = H + 'px'
  const ctx = el.getContext('2d')!
  ctx.scale(dpr, dpr)

  // ── 3. Extract body mask from anatomy PNG ─────────────────────────────────
  const img = new Image()
  img.src = '/anatomy-hero.png'
  await new Promise<void>(r => { img.onload = () => r() })

  const mCvs = document.createElement('canvas')
  mCvs.width = W; mCvs.height = H
  const mCtx = mCvs.getContext('2d')!
  mCtx.drawImage(img, 0, 0, W, H)
  const px = mCtx.getImageData(0, 0, W, H).data

  // luminance > 30 = body pixel (background is near-black ~0-20)
  const mask = new Uint8Array(W * H)
  for (let i = 0; i < W * H; i++) {
    mask[i] = (px[i*4] + px[i*4+1] + px[i*4+2]) / 3 > 30 ? 1 : 0
  }

  // ── 4. Ghost silhouette ───────────────────────────────────────────────────
  ctx.globalAlpha = 0.07
  ctx.drawImage(img, 0, 0, W, H)
  ctx.globalAlpha = 1

  // ── 5. Word list — top 5 terms per body part ──────────────────────────────
  const words: { text: string; score: number; color: string }[] = []
  for (const [bp, terms] of Object.entries(tfidf)) {
    const color = BP_COLORS[bp] ?? '#c9a84c'
    for (const t of terms.slice(0, 7)) {
      words.push({ text: t.term, score: t.score_norm, color })
    }
  }
  words.sort((a, b) => b.score - a.score)

  // ── 6. Body centroid ──────────────────────────────────────────────────────
  let sx = 0, sy = 0, sc = 0
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    if (mask[y*W+x]) { sx += x; sy += y; sc++ }
  }
  const cxB = sc ? Math.round(sx / sc) : W / 2
  const cyB = sc ? Math.round(sy / sc) : H / 2

  // ── 7. Place words — Archimedean spiral ───────────────────────────────────
  const occupied = new Uint8Array(W * H)
  const tmp = document.createElement('canvas').getContext('2d')!

  for (const word of words) {
    const fs   = Math.round(6 + word.score * 4)    // 6–10 px
    const font = `500 ${fs}px monospace`
    tmp.font = font
    const tw = Math.ceil(tmp.measureText(word.text).width)
    const th = fs + 3

    const pos = placeSpiral(cxB, cyB, tw, th, mask, occupied, W, H)
    if (!pos) continue

    markOccupied(pos.x, pos.y, tw + 2, th + 2, occupied, W, H)

    ctx.font        = font
    ctx.shadowColor = word.color
    ctx.shadowBlur  = 9
    ctx.fillStyle   = word.color
    ctx.globalAlpha = 0.55 + word.score * 0.45
    ctx.fillText(word.text, pos.x - tw / 2, pos.y + fs / 2 - 1)
  }
  ctx.shadowBlur  = 0
  ctx.globalAlpha = 1
  ready.value = true
})

// Archimedean spiral r = a·θ, starting from body centroid
function placeSpiral(
  cx: number, cy: number, tw: number, th: number,
  mask: Uint8Array, occ: Uint8Array, W: number, H: number,
): { x: number; y: number } | null {
  let theta = 0
  while (true) {
    const r = 1.1 * theta / (2 * Math.PI)
    if (r > Math.max(W, H)) break
    const x = Math.round(cx + r * Math.cos(theta))
    const y = Math.round(cy + r * Math.sin(theta))
    if (canPlace(x, y, tw, th, mask, occ, W, H)) return { x, y }
    theta += 0.50
  }
  return null
}

function canPlace(
  x: number, y: number, tw: number, th: number,
  mask: Uint8Array, occ: Uint8Array, W: number, H: number,
): boolean {
  const x1 = Math.floor(x - tw / 2) - 1
  const x2 = Math.ceil(x  + tw / 2) + 1
  const y1 = Math.floor(y - th / 2) - 1
  const y2 = Math.ceil(y  + th / 2) + 1
  if (x1 < 0 || y1 < 0 || x2 >= W || y2 >= H) return false
  for (let py = y1; py <= y2; py++)
    for (let px = x1; px <= x2; px++)
      if (!mask[py * W + px] || occ[py * W + px]) return false
  return true
}

function markOccupied(
  x: number, y: number, tw: number, th: number,
  occ: Uint8Array, W: number, H: number,
) {
  const x1 = Math.max(0, Math.floor(x - tw / 2))
  const x2 = Math.min(W - 1, Math.ceil(x  + tw / 2))
  const y1 = Math.max(0, Math.floor(y - th / 2))
  const y2 = Math.min(H - 1, Math.ceil(y  + th / 2))
  for (let py = y1; py <= y2; py++)
    for (let px = x1; px <= x2; px++)
      occ[py * W + px] = 1
}
</script>

<style scoped>
.wc-outer {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
}

.wc-label-bar {
  font-family: var(--font-mono);
  font-size: 0.58rem;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: .08em;
  display: flex;
  align-items: center;
  gap: 6px;
}

.wc-badge {
  font-size: 0.53rem;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 2px;
  background: rgba(0, 212, 255, .10);
  border: 1px solid rgba(0, 212, 255, .25);
  color: #00d4ff;
  letter-spacing: .05em;
}

.wc-canvas {
  display: block;
  border-radius: var(--radius);
}

.wc-loading {
  width: 240px;
  height: 480px;
  background: linear-gradient(90deg, var(--bg3) 25%, var(--bg2) 50%, var(--bg3) 75%);
  background-size: 200% 100%;
  animation: sk-shimmer 1.4s infinite;
  border-radius: var(--radius);
}
@keyframes sk-shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
