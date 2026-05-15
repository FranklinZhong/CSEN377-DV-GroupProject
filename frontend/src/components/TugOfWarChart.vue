<!--
  TugOfWarChart.vue — Vis 3 tug-of-war sentiment chart (v3.5, replaces IsotypeGrid)

  Each body_part is one rope:
  - Center line = 0 (neutral)
  - Knot position: (positive - negative) / (positive + negative), mapped to [-1, +1]
  - Rope color: red-to-green gradient by net sentiment
  - Rope thickness: √-scaled by review count
  - Click a row to open the ReviewList drawer
-->
<template>
  <div class="tow-wrap">
    <header class="tow-head">
      <h3 class="vis-title"><span class="emoji">💬</span> Patient Sentiment Tug-of-War</h3>
      <span class="vis-meta" v-if="totalReviews > 0">
        {{ totalReviews.toLocaleString() }} reviews ·
        {{ bodyParts.length }} body systems
      </span>
    </header>

    <div v-if="loading" class="tow-state">
      <el-skeleton :rows="4" animated />
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
          :class="['tow-row', { 'tow-active': selectedPart === bp }]"
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
            <span class="bp-name">{{ bp }}</span>
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

    <!-- ── Drawer with ReviewList ── -->
    <el-drawer
      v-model="drawerOpen"
      :title="drawerTitle"
      direction="rtl"
      size="540px"
      :close-on-click-modal="true"
    >
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
          <el-tag
            v-for="t in topTerms(selectedPart)"
            :key="t"
            size="small"
            type="info"
            effect="plain"
            style="margin: 3px 4px 0 0"
          >{{ t }}</el-tag>
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
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { api } from '../api/client'
import type { ReviewCluster } from '../api/client'
import ReviewList from './ReviewList.vue'

const props = defineProps<{ drugId: number }>()
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
    if (res.data.success) clusters.value = res.data.data.clusters ?? []
  } catch {} finally {
    loading.value = false
  }
}
watch(() => props.drugId, load, { immediate: true })
</script>

<style scoped>
.tow-wrap { padding: 12px 0; }

.tow-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}
.vis-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: #cbd5e1;
  display: flex; align-items: center; gap: 6px;
}
.vis-meta { font-size: 0.75rem; color: #64748b; }

.tow-state {
  padding: 32px;
  text-align: center;
  color: #64748b;
  font-size: 0.85rem;
}

.tow-axis {
  display: grid;
  grid-template-columns: 64px 1fr 64px;
  font-size: 0.66rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #475569;
  padding: 0 88px 6px;
}
.ax-neg { text-align: right; color: #ef4444; }
.ax-pos { text-align: left;  color: #22c55e; }
.ax-mid { text-align: center; }

.tow-rows {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.tow-row {
  display: grid;
  grid-template-columns: 56px 1fr 130px 56px;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 10px;
  cursor: pointer;
  transition: background .15s, transform .15s;
  animation: tow-in 0.5s ease-out backwards;
  animation-delay: var(--row-delay, 0ms);
}
@keyframes tow-in {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
.tow-row:hover, .tow-active {
  background: #111827;
  transform: translateX(2px);
}

/* Counts */
.tow-count { display: flex; align-items: center; }
.tow-neg-count { justify-content: flex-end; }
.tow-pos-count { justify-content: flex-start; }
.cnt-pill {
  font-size: 0.72rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  padding: 3px 8px;
  border-radius: 8px;
  min-width: 32px;
  text-align: center;
}
.cnt-neg { background: rgba(248,113,113,.15); color: #f87171; }
.cnt-pos { background: rgba(74,222,128,.15);  color: #4ade80; }

/* Rope */
.tow-rope-cell {
  width: 100%;
  height: 50px;
}
.rope-svg {
  width: 100%;
  height: 100%;
  display: block;
}

/* Label */
.tow-label {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  line-height: 1.2;
}
.bp-name {
  font-weight: 600;
  color: #cbd5e1;
  text-transform: capitalize;
  font-size: 0.82rem;
}
.bp-meta {
  font-size: 0.66rem;
  color: #64748b;
  margin-top: 2px;
}
.mixed-badge { color: #fbbf24; }

.tow-hint {
  text-align: center;
  font-size: 0.72rem;
  color: #475569;
  margin-top: 14px;
}

/* ── Drawer ── */
.drawer-body {
  padding: 6px 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.drawer-stats {
  display: flex;
  gap: 8px;
}
.stat-pill {
  flex: 1;
  border-radius: 10px;
  padding: 10px;
  text-align: center;
}
.stat-pill.neg { background: rgba(248,113,113,.12); border: 1px solid rgba(248,113,113,.25); }
.stat-pill.pos { background: rgba(74,222,128,.12);  border: 1px solid rgba(74,222,128,.25); }
.stat-pill.mix { background: rgba(251,191,36,.1);   border: 1px solid rgba(251,191,36,.2); }
.stat-n { display: block; font-size: 1.4rem; font-weight: 700; }
.stat-l { font-size: 0.66rem; color: #64748b; text-transform: uppercase; letter-spacing: .06em; }
.stat-pill.neg .stat-n { color: #f87171; }
.stat-pill.pos .stat-n { color: #4ade80; }
.stat-pill.mix .stat-n { color: #fbbf24; }

.drawer-terms { padding: 0 4px; }
.drawer-section-title {
  font-size: .7rem;
  text-transform: uppercase;
  letter-spacing: .06em;
  color: #475569;
  margin-bottom: 8px;
}
.drawer-list { padding-top: 4px; }
.drawer-disclaimer {
  font-size: 0.68rem;
  color: #334155;
  text-align: center;
  margin-top: 12px;
}
.emoji { font-style: normal; }
</style>
