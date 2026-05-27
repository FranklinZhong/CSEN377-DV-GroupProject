<!--
  ReviewList.vue — 真实评论分页查看器（v4.0）
  - 全自定义深色主题，移除 Element Plus 依赖
  - 搜索 + 排序同行；情感改为彩色 pill 切换按钮
-->
<template>
  <div class="rl-wrap">

    <!-- ── Filter bar ── -->
    <div class="rl-filters">
      <div class="rl-search-row">
        <div class="rl-input-wrap">
          <span class="rl-search-icon">
            <svg width="13" height="13" viewBox="0 0 20 20" fill="none">
              <circle cx="8.5" cy="8.5" r="5.75" stroke="#64748b" stroke-width="1.8"/>
              <line x1="13" y1="13" x2="18" y2="18" stroke="#64748b" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
          </span>
          <input
            v-model="qInput"
            class="rl-input"
            type="text"
            placeholder="Search keywords..."
            @input="debounceSearch"
          />
          <button v-if="qInput" class="rl-clear-btn" @click="clearSearch">✕</button>
        </div>

        <select v-model="sort" class="rl-sort" @change="reload(1)">
          <option value="recent">Most Recent</option>
          <option value="rating_desc">Highest Rated</option>
          <option value="rating_asc">Lowest Rated</option>
        </select>
      </div>

      <!-- Sentiment pills -->
      <div class="rl-pills">
        <button
          v-for="opt in sentimentOptions"
          :key="opt.value"
          :class="['rl-pill', { active: sentiment === opt.value }]"
          :style="sentiment === opt.value ? { borderColor: opt.color, color: opt.color, background: opt.bg } : {}"
          @click="setSentiment(opt.value)"
        >{{ opt.label }}</button>
      </div>
    </div>

    <!-- Stats summary -->
    <div class="rl-summary" v-if="!loading && total > 0">
      <span class="rl-count">{{ total.toLocaleString() }} review{{ total > 1 ? 's' : '' }}</span>
      <span v-if="bodyPart !== 'all'" class="rl-tag">
        in <strong>{{ bodyPart }}</strong>
      </span>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="rl-state">
      <div class="rl-skeleton" v-for="i in 3" :key="i" />
    </div>

    <!-- Empty -->
    <div v-else-if="!reviews.length" class="rl-state rl-empty">
      <p>No reviews match your filters.</p>
    </div>

    <!-- Reviews -->
    <div v-else class="rl-cards">
      <article
        v-for="r in reviews"
        :key="r.id"
        :class="['rl-card', `rl-card-${r.sentiment}`]"
      >
        <header class="rl-card-head">
          <span class="rl-stars" v-if="r.rating !== null">
            <span class="star" v-for="i in 5" :key="i"
                  :class="{ filled: i <= Math.round(r.rating) }">★</span>
          </span>
          <span class="rl-stars-empty" v-else>No rating</span>
          <span :class="['rl-sentiment', `s-${r.sentiment}`]">
            {{ sentimentLabel(r.sentiment) }}
          </span>
          <span class="rl-source">{{ r.source }}</span>
        </header>
        <p class="rl-text">{{ r.review_text }}</p>
        <footer class="rl-card-foot" v-if="r.body_parts.length">
          <span v-for="bp in r.body_parts" :key="bp" class="rl-bp-tag">{{ bp }}</span>
        </footer>
      </article>
    </div>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="rl-pager">
      <button class="rl-page-btn" :disabled="page <= 1" @click="reload(page - 1)">◀ Prev</button>
      <span class="rl-page-info">Page {{ page }} / {{ totalPages }}</span>
      <button class="rl-page-btn" :disabled="page >= totalPages" @click="reload(page + 1)">Next ▶</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { api } from '../api/client'
import type { ReviewRow, ReviewSort } from '../api/client'

const props = defineProps<{
  drugId: number
  initialBodyPart?: string
  initialSentiment?: string
}>()

const sentimentOptions = [
  { value: 'all',      label: 'All',         color: '#60a5fa', bg: 'rgba(96,165,250,.12)' },
  { value: 'positive', label: '😊 Positive', color: '#4ade80', bg: 'rgba(74,222,128,.12)' },
  { value: 'negative', label: '😞 Negative', color: '#f87171', bg: 'rgba(248,113,113,.12)' },
  { value: 'mixed',    label: '😐 Mixed',    color: '#facc15', bg: 'rgba(250,204,21,.12)'  },
  { value: 'neutral',  label: 'Neutral',     color: '#94a3b8', bg: 'rgba(148,163,184,.12)' },
]

const bodyPart  = ref(props.initialBodyPart  ?? 'all')
const sentiment = ref(props.initialSentiment ?? 'all')
const sort      = ref<ReviewSort>('recent')
const qInput    = ref('')
const q         = ref('')
const page      = ref(1)
const pageSize  = 10

const loading    = ref(false)
const reviews    = ref<ReviewRow[]>([])
const total      = ref(0)
const totalPages = ref(0)

let debounceTimer: ReturnType<typeof setTimeout> | null = null
function debounceSearch() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    q.value = qInput.value
    reload(1)
  }, 300)
}

function clearSearch() {
  qInput.value = ''
  q.value = ''
  reload(1)
}

function setSentiment(val: string) {
  sentiment.value = val
  reload(1)
}

async function reload(p = page.value) {
  loading.value = true
  page.value = p
  try {
    const res = await api.getReviewsList(props.drugId, {
      body_part: bodyPart.value,
      sentiment: sentiment.value,
      sort:      sort.value,
      q:         q.value || undefined,
      page:      p,
      page_size: pageSize,
    })
    if (res.data.success) {
      reviews.value    = res.data.data.reviews
      total.value      = res.data.data.total
      totalPages.value = res.data.data.total_pages
    }
  } catch {
    reviews.value = []
    total.value = 0
    totalPages.value = 0
  } finally {
    loading.value = false
  }
}

watch(() => props.initialBodyPart, (val) => {
  bodyPart.value = val ?? 'all'
  reload(1)
})
watch(() => props.drugId, () => reload(1))

onMounted(() => reload(1))

function sentimentLabel(s: string) {
  if (s === 'positive') return '😊 Positive'
  if (s === 'negative') return '😞 Negative'
  if (s === 'mixed')    return '😐 Mixed'
  return 'Neutral'
}
</script>

<style scoped>
.rl-wrap {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* ── Filter bar ── */
.rl-filters {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rl-search-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.rl-input-wrap {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
}

.rl-search-icon {
  position: absolute;
  left: 10px;
  display: flex;
  align-items: center;
  pointer-events: none;
}

.rl-input {
  width: 100%;
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 7px;
  color: #cbd5e1;
  font-size: 0.82rem;
  padding: 6px 30px 6px 32px;
  outline: none;
  transition: border-color .15s;
}
.rl-input::placeholder { color: #475569; }
.rl-input:focus { border-color: #60a5fa; }

.rl-clear-btn {
  position: absolute;
  right: 8px;
  background: none;
  border: none;
  color: #475569;
  cursor: pointer;
  font-size: 0.75rem;
  padding: 2px 4px;
  line-height: 1;
}
.rl-clear-btn:hover { color: #94a3b8; }

.rl-sort {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 7px;
  color: #94a3b8;
  font-size: 0.78rem;
  padding: 6px 10px;
  outline: none;
  cursor: pointer;
  white-space: nowrap;
  transition: border-color .15s;
}
.rl-sort:focus { border-color: #60a5fa; }
.rl-sort option { background: #1e293b; color: #cbd5e1; }

/* Sentiment pills */
.rl-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.rl-pill {
  background: transparent;
  border: 1px solid #334155;
  border-radius: 20px;
  color: #64748b;
  font-size: 0.72rem;
  padding: 3px 11px;
  cursor: pointer;
  transition: border-color .15s, color .15s, background .15s;
  white-space: nowrap;
}
.rl-pill:hover { border-color: #475569; color: #94a3b8; }
.rl-pill.active { font-weight: 600; }

/* ── Summary ── */
.rl-summary {
  font-size: 0.78rem;
  color: #64748b;
}
.rl-count { color: #cbd5e1; font-weight: 600; }
.rl-tag { margin-left: 8px; }
.rl-tag strong { text-transform: capitalize; color: #60a5fa; }

/* ── Skeleton loading ── */
.rl-state { padding: 16px 0; }
.rl-skeleton {
  height: 72px;
  background: linear-gradient(90deg, #1e293b 25%, #253347 50%, #1e293b 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite;
  border-radius: 10px;
  margin-bottom: 8px;
}
@keyframes shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
.rl-empty { text-align: center; color: #64748b; font-size: 0.85rem; }

/* ── Cards ── */
.rl-cards {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rl-card {
  background: #0f172a;
  border-radius: 10px;
  padding: 12px 14px;
  border-left: 3px solid #475569;
  transition: transform .15s, border-left-color .15s;
}
.rl-card:hover { transform: translateX(2px); }
.rl-card-negative { border-left-color: #f87171; }
.rl-card-positive { border-left-color: #4ade80; }
.rl-card-mixed    { border-left-color: #facc15; }
.rl-card-neutral  { border-left-color: #94a3b8; }

.rl-card-head {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.74rem;
  margin-bottom: 6px;
  flex-wrap: wrap;
}
.rl-stars { color: #475569; letter-spacing: 1px; }
.rl-stars-empty { color: #475569; font-style: italic; font-size: 0.72rem; }
.star.filled { color: #fbbf24; }

.rl-sentiment {
  font-size: 0.7rem;
  padding: 2px 8px;
  border-radius: 8px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-weight: 600;
}
.s-negative { background: rgba(248,113,113,.15); color: #f87171; }
.s-positive { background: rgba(74,222,128,.15);  color: #4ade80; }
.s-mixed    { background: rgba(250,204,21,.15);  color: #facc15; }
.s-neutral  { background: rgba(148,163,184,.15); color: #94a3b8; }

.rl-source {
  margin-left: auto;
  color: #475569;
  font-size: 0.7rem;
}

.rl-text {
  color: #cbd5e1;
  font-size: 0.85rem;
  line-height: 1.55;
  margin: 6px 0 8px;
  white-space: pre-wrap;
}

.rl-card-foot {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.rl-bp-tag {
  background: rgba(96,165,250,.1);
  color: #60a5fa;
  font-size: 0.68rem;
  padding: 2px 7px;
  border-radius: 6px;
  text-transform: capitalize;
}

/* ── Pagination ── */
.rl-pager {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 14px;
  padding: 10px 0;
  font-size: 0.82rem;
}

.rl-page-btn {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 6px;
  color: #94a3b8;
  font-size: 0.76rem;
  padding: 5px 12px;
  cursor: pointer;
  transition: border-color .15s, color .15s;
}
.rl-page-btn:hover:not(:disabled) { border-color: #60a5fa; color: #60a5fa; }
.rl-page-btn:disabled { opacity: 0.35; cursor: not-allowed; }

.rl-page-info {
  color: #94a3b8;
  font-variant-numeric: tabular-nums;
  min-width: 100px;
  text-align: center;
}
</style>
