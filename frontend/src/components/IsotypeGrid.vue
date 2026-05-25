<!--
  IsotypeGrid.vue — Vis 3 患者评论可视化（改版）

  改动：
  - 蝴蝶对比图（Butterfly Chart）：负面向左/正面向右
  - 点击行 → 右侧 el-drawer 显示两列评论引文
  - 保留 isotype 小人在条形右侧
-->
<template>
  <div class="iso-wrap">
    <div class="iso-header">
      <h3 class="vis-title">Patient Experience — Positive vs Negative</h3>
      <span class="iso-meta" v-if="totalReviews > 0">
        {{ totalReviews.toLocaleString() }} reviews · {{ bodyParts.length }} systems
      </span>
    </div>

    <div v-if="loading" class="iso-placeholder">
      <el-skeleton :rows="4" animated />
    </div>
    <div v-else-if="!clusters.length" class="iso-placeholder">
      <p>No patient review data available for this drug.</p>
    </div>

    <template v-else>
      <!-- Column headers -->
      <div class="butterfly-header">
        <span class="bh-neg">← Negative</span>
        <span class="bh-center">Body System</span>
        <span class="bh-pos">Positive →</span>
      </div>

      <!-- Butterfly rows -->
      <div class="butterfly-grid">
        <div
          v-for="part in bodyParts"
          :key="part"
          class="bf-row"
          :class="{ 'bf-active': selectedPart === part }"
          @click="openDrawer(part)"
          title="Click to see reviews"
        >
          <!-- Negative bar (extends left from centre) -->
          <div class="bar-cell neg-cell">
            <div class="bar-neg"
                 :style="{ width: barWidth(part, 'negative') + '%' }">
              <span class="bar-figures">
                {{ figures(part,'negative') }}
              </span>
            </div>
            <span class="bar-count neg-count">
              {{ countOf(part,'negative') }}
            </span>
          </div>

          <!-- Centre label -->
          <div class="bf-label" :class="{ 'bf-label-active': selectedPart === part }">
            {{ part }}
            <span v-if="mixedCount(part)" class="mixed-badge">
              +{{ mixedCount(part) }} mixed
            </span>
          </div>

          <!-- Positive bar (extends right from centre) -->
          <div class="bar-cell pos-cell">
            <span class="bar-count pos-count">
              {{ countOf(part,'positive') }}
            </span>
            <div class="bar-pos"
                 :style="{ width: barWidth(part, 'positive') + '%' }">
              <span class="bar-figures">
                {{ figures(part,'positive') }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <p class="iso-hint">Click any row to read reviews</p>
      <p class="data-note">Source: WebMD Drug Reviews · VADER sentiment analysis</p>
    </template>

    <!-- ── Review Drawer ── -->
    <el-drawer
      v-model="drawerOpen"
      :title="`${selectedPart} — Patient Reviews`"
      direction="rtl"
      size="480px"
      :close-on-click-modal="true"
    >
      <div class="drawer-body" v-if="selectedPart">
        <!-- Summary stats -->
        <div class="drawer-stats">
          <div class="stat-pill neg">
            <span class="stat-n">{{ countOf(selectedPart,'negative') }}</span>
            <span class="stat-l">Negative</span>
          </div>
          <div class="stat-pill mix">
            <span class="stat-n">{{ mixedCount(selectedPart) }}</span>
            <span class="stat-l">Mixed</span>
          </div>
          <div class="stat-pill pos">
            <span class="stat-n">{{ countOf(selectedPart,'positive') }}</span>
            <span class="stat-l">Positive</span>
          </div>
        </div>

        <!-- Top terms -->
        <div class="drawer-section">
          <p class="drawer-section-title">Top mentioned terms</p>
          <div class="terms-row">
            <div v-for="sent in ['negative','positive']" :key="sent" class="terms-col">
              <p class="terms-label" :class="sent">{{ sent }}</p>
              <el-tag
                v-for="t in termsOf(selectedPart, sent)"
                :key="t"
                size="small"
                effect="plain"
                :type="sent === 'negative' ? 'danger' : 'success'"
                style="margin:3px 3px 0 0"
              >{{ t }}</el-tag>
            </div>
          </div>
        </div>

        <!-- Two-column quotes -->
        <div class="drawer-section">
          <p class="drawer-section-title">What patients say</p>
          <div class="quotes-cols">
            <div class="quotes-col">
              <p class="quotes-label neg">😞 Negative experiences</p>
              <div
                v-for="(q, i) in quotesOf(selectedPart,'negative')"
                :key="i"
                class="quote-card neg-card"
              >{{ q }}</div>
              <p v-if="!quotesOf(selectedPart,'negative').length" class="no-quotes">
                No negative reviews recorded.
              </p>
            </div>
            <div class="quotes-col">
              <p class="quotes-label pos">😊 Positive experiences</p>
              <div
                v-for="(q, i) in quotesOf(selectedPart,'positive')"
                :key="i"
                class="quote-card pos-card"
              >{{ q }}</div>
              <p v-if="!quotesOf(selectedPart,'positive').length" class="no-quotes">
                No positive reviews recorded.
              </p>
            </div>
          </div>
        </div>

        <!-- Mixed reviews -->
        <div v-if="quotesOf(selectedPart,'mixed').length" class="drawer-section">
          <p class="drawer-section-title">Mixed experiences</p>
          <div
            v-for="(q, i) in quotesOf(selectedPart,'mixed')"
            :key="i"
            class="quote-card mix-card"
          >{{ q }}</div>
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

const props = defineProps<{ drugId: number }>()
defineEmits<{ highlight: [part: string] }>()

const loading     = ref(false)
const clusters    = ref<ReviewCluster[]>([])
const drawerOpen  = ref(false)
const selectedPart = ref<string | null>(null)

// ── Derived ──────────────────────────────────────────────────────────────

const totalReviews = computed(() =>
  clusters.value.reduce((s, c) => s + c.review_count, 0)
)

// {body_part: {sentiment: cluster}}
const clusterMap = computed<Record<string, Record<string, ReviewCluster>>>(() => {
  const map: Record<string, Record<string, ReviewCluster>> = {}
  for (const c of clusters.value) {
    if (!map[c.body_part]) map[c.body_part] = {}
    map[c.body_part][c.sentiment] = c
  }
  return map
})

// Sort body parts by total reviews
const bodyParts = computed(() => {
  const totals: Record<string, number> = {}
  for (const c of clusters.value)
    totals[c.body_part] = (totals[c.body_part] ?? 0) + c.review_count
  return Object.keys(totals).sort((a, b) => totals[b] - totals[a]).slice(0, 14)
})

// Max count for bar scaling
const maxCount = computed(() => {
  let m = 0
  for (const part of bodyParts.value) {
    m = Math.max(m, countOf(part,'positive'), countOf(part,'negative'))
  }
  return m || 1
})

function countOf(part: string, sent: string): number {
  return clusterMap.value[part]?.[sent]?.review_count ?? 0
}
function mixedCount(part: string): number {
  return countOf(part,'mixed') + countOf(part,'neutral')
}
function barWidth(part: string, sent: string): number {
  return Math.max(2, (countOf(part, sent) / maxCount.value) * 100)
}
function figures(part: string, sent: string): string {
  const n = Math.round((countOf(part, sent) / maxCount.value) * 8)
  return sent === 'negative' ? '♟'.repeat(Math.max(1,n)) : '♟'.repeat(Math.max(1,n))
}
function termsOf(part: string | null, sent: string): string[] {
  if (!part) return []
  return clusterMap.value[part]?.[sent]?.top_terms ?? []
}
function quotesOf(part: string | null, sent: string): string[] {
  if (!part) return []
  return (clusterMap.value[part]?.[sent]?.representative_quotes ?? []).slice(0, 8)
}

function openDrawer(part: string) {
  selectedPart.value = part
  drawerOpen.value = true
}

// ── Load ─────────────────────────────────────────────────────────────────
async function load(id: number) {
  loading.value = true
  clusters.value = []
  try {
    const res = await api.getReviews(id)
    if (res.data.success) clusters.value = res.data.data.clusters ?? []
  } catch {}
  finally { loading.value = false }
}

watch(() => props.drugId, load, { immediate: true })
</script>

<style scoped>
.iso-wrap { padding: 12px 0; }

.iso-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 16px;
}
.vis-title { font-size: .92rem; font-weight: 600; color: #cbd5e1; }
.iso-meta  { font-size: .75rem; color: #64748b; }
.iso-placeholder { padding: 32px; text-align: center; color: #64748b; }

/* ── Butterfly chart ── */
.butterfly-header {
  display: grid;
  grid-template-columns: 1fr 110px 1fr;
  text-align: center;
  font-size: .68rem;
  text-transform: uppercase;
  letter-spacing: .06em;
  color: #475569;
  margin-bottom: 8px;
  padding: 0 4px;
}
.bh-neg { text-align: right; color: #f87171; }
.bh-pos { text-align: left;  color: #4ade80; }

.butterfly-grid { display: flex; flex-direction: column; gap: 5px; }

.bf-row {
  display: grid;
  grid-template-columns: 1fr 110px 1fr;
  align-items: center;
  gap: 0;
  cursor: pointer;
  border-radius: 8px;
  padding: 3px 4px;
  transition: background .15s;
}
.bf-row:hover, .bf-active {
  background: #1e293b;
}

/* Bar cells */
.bar-cell {
  display: flex;
  align-items: center;
}
.neg-cell {
  justify-content: flex-end;
  flex-direction: row-reverse; /* bar grows from centre outward */
}
.pos-cell {
  justify-content: flex-start;
}

.bar-neg, .bar-pos {
  height: 22px;
  border-radius: 3px;
  display: flex;
  align-items: center;
  min-width: 4px;
  transition: width .4s ease;
  overflow: hidden;
}
.bar-neg {
  background: linear-gradient(to left, #f87171, #dc2626);
  justify-content: flex-end;
  padding-right: 4px;
}
.bar-pos {
  background: linear-gradient(to right, #4ade80, #16a34a);
  justify-content: flex-start;
  padding-left: 4px;
}
.bar-figures {
  font-size: .55rem;
  color: rgba(255,255,255,.5);
  white-space: nowrap;
  overflow: hidden;
}
.bar-count {
  font-size: .7rem;
  color: #64748b;
  min-width: 28px;
  flex-shrink: 0;
}
.neg-count { text-align: right; padding-right: 5px; }
.pos-count { text-align: left;  padding-left: 5px; }

/* Centre label */
.bf-label {
  text-align: center;
  font-size: .72rem;
  font-weight: 600;
  color: #94a3b8;
  text-transform: capitalize;
  padding: 0 6px;
  line-height: 1.3;
}
.bf-label-active { color: #60a5fa; }
.mixed-badge {
  display: block;
  font-size: .6rem;
  color: #fbbf24;
  font-weight: 400;
}

.iso-hint {
  text-align: center;
  font-size: .72rem;
  color: #334155;
  margin-top: 12px;
}
.data-note { font-size: .68rem; color: #334155; margin-top: 6px; text-align: center; }

/* ── Drawer ── */
.drawer-body { padding: 4px 0; }

.drawer-stats {
  display: flex; gap: 12px; margin-bottom: 24px;
}
.stat-pill {
  flex: 1; border-radius: 10px; padding: 12px;
  text-align: center;
}
.stat-pill.neg { background: rgba(248,113,113,.12); border: 1px solid rgba(248,113,113,.25); }
.stat-pill.pos { background: rgba(74,222,128,.12);  border: 1px solid rgba(74,222,128,.25); }
.stat-pill.mix { background: rgba(251,191,36,.1);   border: 1px solid rgba(251,191,36,.2); }
.stat-n { display: block; font-size: 1.6rem; font-weight: 700; }
.stat-l { font-size: .72rem; color: #64748b; text-transform: uppercase; letter-spacing:.06em; }
.stat-pill.neg .stat-n { color: #f87171; }
.stat-pill.pos .stat-n { color: #4ade80; }
.stat-pill.mix .stat-n { color: #fbbf24; }

.drawer-section { margin-bottom: 24px; }
.drawer-section-title {
  font-size: .72rem; text-transform: uppercase;
  letter-spacing: .07em; color: #475569;
  margin-bottom: 10px;
}

.terms-row { display: flex; gap: 16px; }
.terms-col { flex: 1; }
.terms-label {
  font-size: .72rem; font-weight: 600;
  text-transform: capitalize; margin-bottom: 6px;
}
.terms-label.negative { color: #f87171; }
.terms-label.positive { color: #4ade80; }

.quotes-cols { display: flex; gap: 14px; }
.quotes-col { flex: 1; }
.quotes-label {
  font-size: .75rem; font-weight: 600; margin-bottom: 8px;
}
.quotes-label.neg { color: #f87171; }
.quotes-label.pos { color: #4ade80; }

.quote-card {
  background: #111827;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: .8rem;
  line-height: 1.5;
  color: #94a3b8;
  margin-bottom: 8px;
  border-left: 3px solid;
}
.neg-card { border-color: #f87171; }
.pos-card { border-color: #4ade80; }
.mix-card { border-color: #fbbf24; }
.no-quotes { font-size: .78rem; color: #334155; font-style: italic; }

.drawer-disclaimer {
  font-size: .68rem; color: #334155;
  text-align: center; margin-top: 24px;
}
</style>
