<!--
  ReviewList.vue — Paginated patient review viewer (v3.5)

  props:
    drugId           drug id
    initialBodyPart  default body_part filter ('all' or a specific part e.g. 'stomach')
    initialSentiment default sentiment filter

  Fetches paginated data from /api/drugs/{id}/reviews/list
-->
<template>
  <div class="rl-wrap">
    <!-- Filters bar -->
    <div class="rl-filters">
      <el-input
        v-model="qInput"
        size="small"
        clearable
        placeholder="Search keywords..."
        class="rl-search"
        @input="debounceSearch"
      >
        <template #prefix>🔍</template>
      </el-input>

      <el-select v-model="sentiment" size="small" class="rl-select"
                 @change="reload(1)">
        <el-option label="All sentiments" value="all" />
        <el-option label="😞 Negative" value="negative" />
        <el-option label="😐 Mixed"    value="mixed" />
        <el-option label="😊 Positive" value="positive" />
        <el-option label="Neutral"     value="neutral" />
      </el-select>

      <el-select v-model="sort" size="small" class="rl-select"
                 @change="reload(1)">
        <el-option label="Most Recent"   value="recent" />
        <el-option label="Highest Rated" value="rating_desc" />
        <el-option label="Lowest Rated"  value="rating_asc" />
      </el-select>
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
      <el-skeleton :rows="3" animated />
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
          <span v-for="bp in r.body_parts" :key="bp" class="rl-bp-tag">
            {{ bp }}
          </span>
        </footer>
      </article>
    </div>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="rl-pager">
      <el-button
        size="small" plain :disabled="page <= 1" @click="reload(page - 1)"
      >◀ Prev</el-button>
      <span class="rl-page-info">Page {{ page }} / {{ totalPages }}</span>
      <el-button
        size="small" plain :disabled="page >= totalPages" @click="reload(page + 1)"
      >Next ▶</el-button>
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

// Reload when parent changes body_part or drugId
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
  gap: 14px;
}

/* Filters */
.rl-filters {
  display: grid;
  grid-template-columns: 1fr 140px 140px;
  gap: 8px;
}
.rl-search { width: 100%; }
.rl-select { width: 100%; }

.rl-summary {
  font-size: 0.78rem;
  color: #64748b;
}
.rl-count { color: #cbd5e1; font-weight: 600; }
.rl-tag { margin-left: 8px; }
.rl-tag strong {
  text-transform: capitalize;
  color: #60a5fa;
}

/* State */
.rl-state {
  padding: 24px;
  text-align: center;
}
.rl-empty { color: #64748b; font-size: 0.85rem; }

/* Cards */
.rl-cards {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.rl-card {
  background: #0f172a;
  border-radius: 10px;
  padding: 12px 14px;
  border-left: 3px solid #475569;
  transition: transform .15s;
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
.s-positive { background: rgba(74,222,128,.15); color: #4ade80; }
.s-mixed    { background: rgba(250,204,21,.15); color: #facc15; }
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

/* Pager */
.rl-pager {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 14px;
  padding: 12px 0;
  font-size: 0.82rem;
}
.rl-page-info {
  color: #94a3b8;
  font-variant-numeric: tabular-nums;
  min-width: 100px;
  text-align: center;
}
</style>
