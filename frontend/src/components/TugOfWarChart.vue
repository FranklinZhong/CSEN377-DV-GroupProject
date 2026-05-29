<!--
  TugOfWarChart.vue — Vis 3 tug-of-war chart (v3.5, replaces IsotypeGrid butterfly chart)

  Each body_part = one rope
  - Center line = 0 (neutral)
  - Knot position: (positive - negative) / (positive + negative), mapped to [-1, +1]
  - Rope color: red-to-green gradient by net sentiment
  - Rope thickness: sqrt-scaled by review count
  - Row click → opens drawer with embedded ReviewList
-->
<template>
  <div class="tow-wrap">
    <header class="tow-head">
      <h3 class="vis-title">Patient Sentiment Tug-of-War</h3>
      <span class="vis-meta" v-if="totalReviews > 0">
        {{ totalReviews.toLocaleString() }} reviews ·
        {{ bodyParts.length }} body systems
      </span>
    </header>

    <div v-if="loading" class="tow-state">
      <div class="tow-skeleton">
        <div class="sk-row" v-for="i in 4" :key="i"></div>
      </div>
    </div>

    <div v-else-if="!clusters.length" class="tow-state">
      <p>No patient review data available for this drug.</p>
    </div>

    <template v-else>
      <!-- Column labels -->
      <div class="tow-axis">
        <span class="ax-neg">← More Negative</span>
        <span class="ax-mid">Balanced</span>
        <span class="ax-pos">More Positive →</span>
      </div>

      <!-- Rows -->
      <div class="tow-rows">
        <div
          v-for="(bp, i) in bodyParts"
          :key="bp"
          :class="['tow-row', { 'tow-active': selectedPart === bp || props.hoveredPart === bp }]"
          :style="{ '--row-delay': `${i * 50}ms` }"
          @click="openDrawer(bp)"
          @mouseenter="$emit('highlight', bp)"
          @mouseleave="$emit('highlight', '')"
        >
          <!-- Left count -->
          <div class="tow-count tow-neg-count">
            <span class="cnt-pill cnt-neg">{{ countOf(bp, 'negative') }}</span>
          </div>

          <!-- Rope SVG -->
          <div class="tow-rope-cell">
            <svg viewBox="0 0 400 50" preserveAspectRatio="none" class="rope-svg">
              <defs>
                <linearGradient :id="`grad-${i}`" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%"   stop-color="#dc2626"/>
                  <stop offset="50%"  :stop-color="centerColor(bp)"/>
                  <stop offset="100%" stop-color="#16a34a"/>
                </linearGradient>
              </defs>
              <!-- center marker -->
              <line x1="200" y1="6" x2="200" y2="44"
                    stroke="#334155" stroke-width="1.5" stroke-dasharray="2 3"/>

              <!-- rope -->
              <line x1="20" y1="25" x2="380" y2="25"
                    :stroke="`url(#grad-${i})`"
                    :stroke-width="ropeWidth(bp)"
                    stroke-linecap="round"/>

              <!-- knot -->
              <circle :cx="knotX(bp)" cy="25" :r="knotR(bp)"
                      :fill="centerColor(bp)"
                      stroke="#0b1224" stroke-width="2"/>
              <circle :cx="knotX(bp)" cy="25" :r="knotR(bp) - 3"
                      fill="rgba(255,255,255,.18)"/>
            </svg>
          </div>

          <!-- Body part label -->
          <div class="tow-label">
            <span class="bp-name" :style="{ color: centerColor(bp) }">{{ bodyPartLabel(bp) }}</span>
            <span class="bp-meta">
              {{ totalOf(bp) }} reviews
              <span v-if="mixedCount(bp)" class="mixed-badge">
                · +{{ mixedCount(bp) }} mixed
              </span>
            </span>
          </div>

          <!-- Right count -->
          <div class="tow-count tow-pos-count">
            <span class="cnt-pill cnt-pos">{{ countOf(bp, 'positive') }}</span>
          </div>
        </div>
      </div>

      <p class="tow-hint">Click a row to read actual patient reviews</p>
    </template>

  </div>

  <!-- ── Custom Drawer ── -->
  <Teleport to="body">
    <div class="tow-drawer" :class="{ open: drawerOpen }">
      <div class="tow-drawer-overlay" @click="drawerOpen = false" />
      <div class="tow-drawer-panel">
        <div class="tow-drawer-header">
          <span class="tow-drawer-title">{{ drawerTitle }}</span>
          <button class="tow-drawer-close" @click="drawerOpen = false">✕</button>
        </div>
        <div class="drawer-body" v-if="selectedPart">
          <!-- Compact stat strip -->
          <div class="drawer-stats">
            <div class="stat-pill neg">
              <span class="stat-n">{{ countOf(selectedPart, 'negative') }}</span>
              <span class="stat-l">Negative</span>
            </div>
            <div class="stat-pill mix" v-if="mixedCount(selectedPart)">
              <span class="stat-n">{{ mixedCount(selectedPart) }}</span>
              <span class="stat-l">Mixed</span>
            </div>
            <div class="stat-pill pos">
              <span class="stat-n">{{ countOf(selectedPart, 'positive') }}</span>
              <span class="stat-l">Positive</span>
            </div>
          </div>

          <!-- Top terms -->
          <div class="drawer-terms" v-if="topTerms(selectedPart).length">
            <p class="drawer-section-title">Top terms</p>
            <div class="drawer-terms-list">
              <span v-for="t in topTerms(selectedPart)" :key="t" class="term-tag">{{ t }}</span>
            </div>
          </div>

          <!-- Real reviews list -->
          <div class="drawer-list">
            <ReviewList
              :drug-id="props.drugId"
              :initial-body-part="selectedPart"
              initial-sentiment="all"
            />
          </div>

          <p class="drawer-disclaimer">
            Reviews from WebMD. For informational purposes only — not medical advice.
          </p>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { api } from '../api/client'
import type { ReviewCluster } from '../api/client'
import ReviewList from './ReviewList.vue'

const props = defineProps<{ drugId: number; hoveredPart?: string | null }>()
defineEmits<{ highlight: [part: string] }>()

const loading      = ref(false)
const clusters     = ref<ReviewCluster[]>([])
const drawerOpen   = ref(false)
const selectedPart = ref<string | null>(null)

// {body_part: {sentiment: cluster}}
const clusterMap = computed<Record<string, Record<string, ReviewCluster>>>(() => {
  const map: Record<string, Record<string, ReviewCluster>> = {}
  for (const c of clusters.value) {
    if (!map[c.body_part]) map[c.body_part] = {}
    map[c.body_part][c.sentiment] = c
  }
  return map
})

const bodyParts = computed(() => {
  // sort by total review count desc, top 12
  const totals: Record<string, number> = {}
  for (const c of clusters.value)
    totals[c.body_part] = (totals[c.body_part] ?? 0) + c.review_count
  return Object.keys(totals).sort((a, b) => totals[b] - totals[a]).slice(0, 12)
})

const totalReviews = computed(() =>
  clusters.value.reduce((s, c) => s + c.review_count, 0)
)

const maxTotal = computed(() => {
  let m = 0
  for (const bp of bodyParts.value) m = Math.max(m, totalOf(bp))
  return m || 1
})

function countOf(part: string, sent: string): number {
  return clusterMap.value[part]?.[sent]?.review_count ?? 0
}
function totalOf(part: string): number {
  return ['positive', 'negative', 'mixed', 'neutral']
    .reduce((s, k) => s + countOf(part, k), 0)
}
function mixedCount(part: string): number {
  return countOf(part, 'mixed') + countOf(part, 'neutral')
}
function netSentiment(part: string): number {
  const p = countOf(part, 'positive')
  const n = countOf(part, 'negative')
  if (p + n === 0) return 0
  return (p - n) / (p + n)
}
function knotX(part: string): number {
  const net = netSentiment(part)
  const center = 200
  const span = 160      // ±160 from center
  return center + net * span
}
function knotR(part: string): number {
  const t = totalOf(part)
  return 8 + Math.min(8, Math.sqrt(t / maxTotal.value) * 8)
}
function ropeWidth(part: string): number {
  const t = totalOf(part)
  return 3 + Math.sqrt(t / maxTotal.value) * 5
}
function centerColor(part: string): string {
  const net = netSentiment(part)
  if (net > 0.25)  return '#4ade80'
  if (net > 0)     return '#86efac'
  if (net > -0.25) return '#facc15'
  if (net > -0.6)  return '#fb923c'
  return '#f87171'
}
const bpLabels: Record<string, string> = {
  brain: 'Brain', eye: 'Eyes', ear: 'Ears', heart: 'Heart',
  lung: 'Lungs', liver: 'Liver', stomach: 'Stomach', kidney: 'Kidneys',
  skin: 'Skin', muscle: 'Muscles', blood: 'Blood System',
  vascular: 'Vascular System', endocrine: 'Endocrine System',
  reproductive: 'Reproductive System', immune: 'Immune System',
}
function bodyPartLabel(part: string): string {
  return bpLabels[part] ?? (part.charAt(0).toUpperCase() + part.slice(1))
}

function topTerms(part: string | null): string[] {
  if (!part) return []
  const all: string[] = []
  for (const sent of ['negative', 'mixed', 'positive']) {
    const t = clusterMap.value[part]?.[sent]?.top_terms ?? []
    all.push(...t)
  }
  return [...new Set(all)].slice(0, 12)
}

const drawerTitle = computed(() =>
  selectedPart.value
    ? `Reviews — ${selectedPart.value.charAt(0).toUpperCase() + selectedPart.value.slice(1)}`
    : ''
)

function openDrawer(part: string) {
  selectedPart.value = part
  drawerOpen.value = true
}

async function load(id: number) {
  loading.value = true
  clusters.value = []
  try {
    const res = await api.getReviews(id)
    if (res.data.success) clusters.value = Array.isArray(res.data.data?.clusters) ? res.data.data.clusters : []
  } catch {} finally {
    loading.value = false
  }
}
watch(() => props.drugId, load, { immediate: true })
</script>

<style scoped>
.tow-wrap { padding: 12px 0; color: var(--text); }

.tow-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}
.vis-title {
  font-family: var(--font-mono);
  font-size: 0.8rem; font-weight: 700; color: var(--gold);
  text-transform: uppercase; letter-spacing: .08em; margin: 0;
}
.vis-meta { font-family: var(--font-mono); font-size: 0.78rem; color: var(--muted); }

.tow-state { padding: 32px; text-align: center; color: var(--muted); font-size: 0.85rem; }

.tow-skeleton { display: flex; flex-direction: column; gap: 8px; }
.sk-row {
  height: 44px;
  background: linear-gradient(90deg, var(--bg3) 25%, var(--bg2) 50%, var(--bg3) 75%);
  background-size: 200% 100%;
  animation: tow-shimmer 1.4s infinite;
  border-radius: var(--radius);
}
@keyframes tow-shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.tow-axis {
  display: grid;
  grid-template-columns: 64px 1fr 64px;
  font-family: var(--font-mono);
  font-size: 0.70rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--muted);
  padding: 0 88px 6px;
}
.ax-neg { text-align: right; color: var(--side); }
.ax-pos { text-align: left;  color: var(--benefit); }
.ax-mid { text-align: center; }

.tow-rows { display: flex; flex-direction: column; gap: 4px; }

.tow-row {
  display: grid;
  grid-template-columns: 56px 1fr 130px 56px;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: var(--radius);
  border-left: 2px solid transparent;
  cursor: pointer;
  transition: background .12s, border-color .12s;
  animation: tow-in 0.5s ease-out backwards;
  animation-delay: var(--row-delay, 0ms);
}
@keyframes tow-in {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
.tow-row:hover, .tow-active {
  background: var(--bg3);
  border-left-color: var(--gold);
}

/* Counts */
.tow-count { display: flex; align-items: center; }
.tow-neg-count { justify-content: flex-end; }
.tow-pos-count { justify-content: flex-start; }
.cnt-pill {
  font-family: var(--font-mono);
  font-size: 0.78rem; font-weight: 700;
  font-variant-numeric: tabular-nums;
  padding: 3px 8px; border-radius: 2px;
  min-width: 32px; text-align: center;
}
.cnt-neg { background: rgba(239,68,68,.12); color: #f87171; }
.cnt-pos { background: rgba(34,197,94,.12); color: #4ade80; }

/* Rope */
.tow-rope-cell { width: 100%; height: 50px; }
.rope-svg { width: 100%; height: 100%; display: block; }

/* Label */
.tow-label { display: flex; flex-direction: column; align-items: flex-start; line-height: 1.2; }
.bp-name {
  font-family: var(--font-mono);
  font-weight: 600; color: var(--text); text-transform: capitalize; font-size: 0.84rem;
}
.bp-meta { font-size: 0.72rem; color: var(--muted); margin-top: 2px; }
.mixed-badge { color: #fbbf24; }

.tow-hint {
  text-align: center; font-family: var(--font-mono);
  font-size: 0.74rem; color: var(--muted); margin-top: 14px; opacity: 0.7;
}

/* ── Custom Drawer ── */
.tow-drawer-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.5);
  opacity: 0; pointer-events: none;
  transition: opacity 0.3s;
  z-index: 900;
}
.tow-drawer-panel {
  position: fixed; right: 0; top: 0;
  height: 100vh; width: 540px;
  background: var(--bg2); border-left: 1px solid var(--border);
  transform: translateX(100%);
  transition: transform 0.3s cubic-bezier(0.4,0,0.2,1);
  z-index: 901;
  display: flex; flex-direction: column;
  overflow: hidden;
}
.tow-drawer.open .tow-drawer-overlay { opacity: 1; pointer-events: auto; }
.tow-drawer.open .tow-drawer-panel   { transform: translateX(0); }

.tow-drawer-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.tow-drawer-title {
  font-family: var(--font-mono);
  font-size: 0.78rem; text-transform: uppercase;
  letter-spacing: .08em; color: var(--gold);
}
.tow-drawer-close {
  background: none; border: none;
  color: var(--muted); font-size: 1rem; cursor: pointer;
  padding: 4px 8px; border-radius: var(--radius);
  transition: color .15s;
}
.tow-drawer-close:hover { color: var(--gold); }

/* Drawer contents */
.drawer-body {
  padding: 16px 20px;
  display: flex; flex-direction: column; gap: 16px;
  overflow-y: auto; flex: 1;
}
.drawer-stats { display: flex; gap: 8px; }
.stat-pill {
  flex: 1; border-radius: var(--radius); padding: 10px; text-align: center;
}
.stat-pill.neg { background: rgba(239,68,68,.10); border: 1px solid rgba(239,68,68,.2); }
.stat-pill.pos { background: rgba(34,197,94,.10); border: 1px solid rgba(34,197,94,.2); }
.stat-pill.mix { background: rgba(245,158,11,.08); border: 1px solid rgba(245,158,11,.15); }
.stat-n { display: block; font-family: var(--font-mono); font-size: 1.4rem; font-weight: 700; }
.stat-l { font-family: var(--font-mono); font-size: 0.70rem; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; }
.stat-pill.neg .stat-n { color: #f87171; }
.stat-pill.pos .stat-n { color: #4ade80; }
.stat-pill.mix .stat-n { color: #fbbf24; }

.drawer-terms { padding: 0 2px; }
.drawer-section-title {
  font-family: var(--font-mono);
  font-size: 0.72rem; text-transform: uppercase; letter-spacing: .06em;
  color: var(--muted); margin: 0 0 8px;
}
.drawer-terms-list { display: flex; flex-wrap: wrap; gap: 4px; }
.term-tag {
  font-family: var(--font-mono);
  font-size: 0.72rem; padding: 2px 8px; border-radius: 2px;
  background: var(--bg3); color: var(--text2); border: 1px solid var(--border2);
}
.drawer-list { padding-top: 4px; }
.drawer-disclaimer {
  font-family: var(--font-mono);
  font-size: 0.72rem; color: var(--muted); text-align: center; opacity: 0.6;
}
</style>
