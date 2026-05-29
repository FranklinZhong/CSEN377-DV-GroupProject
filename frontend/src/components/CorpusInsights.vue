<template>
  <section class="corpus-insights">
    <div class="ci-header">
      <span class="ci-badge">NLP ANALYSIS</span>
      <h2 class="ci-title">Patient Review Corpus Insights</h2>
      <p class="ci-desc">
        TF-IDF discriminative term extraction + VADER sentiment analysis
        across <strong>{{ totalReviews.toLocaleString() }}</strong> patient reviews
        mapped to 15 body systems.
      </p>
    </div>

    <div v-if="loading" class="ci-loading">
      <div class="ci-skeleton" v-for="i in 6" :key="i" />
    </div>

    <div v-else-if="data" class="ci-body">

      <!-- ── Left: Sentiment bars ──────────────────────────────── -->
      <div class="ci-left">
        <div class="ci-section-label">
          <span class="method-tag">VADER Sentiment</span>
          Positive vs Negative by Body System
        </div>

        <div class="sentiment-list">
          <div
            v-for="row in data.sentiment"
            :key="row.body_part"
            class="sent-row"
          >
            <span class="bp-label">{{ BP_LABELS[row.body_part] ?? capitalize(row.body_part) }}</span>
            <div class="bar-track">
              <div
                class="bar-seg bar-pos"
                :style="{ width: row.positive_pct + '%' }"
                :title="`Positive: ${row.positive_pct}%`"
              />
              <div
                class="bar-seg bar-neu"
                :style="{ width: row.neutral_pct + '%' }"
                :title="`Neutral: ${row.neutral_pct}%`"
              />
              <div
                class="bar-seg bar-neg"
                :style="{ width: row.negative_pct + '%' }"
                :title="`Negative: ${row.negative_pct}%`"
              />
            </div>
            <span class="bar-pct neg-label">{{ row.negative_pct }}%<span class="pct-sub"> neg</span></span>
            <span class="vol-label">{{ formatK(row.total) }}</span>
          </div>
        </div>

        <div class="sent-legend">
          <span class="leg-item"><span class="leg-dot pos" />Positive</span>
          <span class="leg-item"><span class="leg-dot neu" />Neutral</span>
          <span class="leg-item"><span class="leg-dot neg" />Negative</span>
          <span class="leg-note">Sorted by review volume</span>
        </div>
      </div>

      <!-- ── Right: TF-IDF term grid ───────────────────────────── -->
      <div class="ci-right">
        <div class="ci-section-label">
          <span class="method-tag">TF-IDF</span>
          Discriminative Terms per Body System
        </div>

        <div class="tfidf-grid">
          <div
            v-for="[bp, terms] in tfidfEntries"
            :key="bp"
            class="bp-card"
          >
            <span class="bpc-name">{{ BP_LABELS[bp] ?? capitalize(bp) }}</span>
            <div class="bpc-terms">
              <span
                v-for="t in terms"
                :key="t.term"
                class="term-chip"
                :style="{ opacity: 0.45 + t.score_norm * 0.55 }"
                :title="`TF-IDF score: ${t.score_norm.toFixed(2)}`"
              >{{ t.term }}</span>
            </div>
          </div>
        </div>

        <p class="tfidf-note">
          Terms with highest TF-IDF score — most discriminative vocabulary
          for each body system in the patient review corpus.
        </p>
      </div>

    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '../api/client'

interface SentimentRow {
  body_part: string
  positive: number; negative: number; neutral: number; total: number
  positive_pct: number; negative_pct: number; neutral_pct: number
}
interface TfidfTerm { term: string; score_norm: number; rank: number }
interface CorpusData {
  tfidf: Record<string, TfidfTerm[]>
  sentiment: SentimentRow[]
}

const loading = ref(true)
const data    = ref<CorpusData | null>(null)

const BP_LABELS: Record<string, string> = {
  brain: 'Brain / CNS', heart: 'Heart', lung: 'Lungs', liver: 'Liver',
  stomach: 'Stomach', kidney: 'Kidneys', immune: 'Immune', endocrine: 'Endocrine',
  muscle: 'Muscles', blood: 'Blood', skin: 'Skin', vascular: 'Vascular',
  eye: 'Eyes', ear: 'Ears', reproductive: 'Reproductive',
}

const capitalize = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)
const formatK    = (n: number) => n >= 1000 ? (n / 1000).toFixed(0) + 'K' : String(n)

const totalReviews = computed(() =>
  data.value?.sentiment.reduce((s, r) => s + r.total, 0) ?? 0
)

const tfidfEntries = computed(() =>
  Object.entries(data.value?.tfidf ?? {})
    .sort((a, b) => {
      // Order by sentiment total (same order as left panel)
      const order = data.value?.sentiment.map(r => r.body_part) ?? []
      return order.indexOf(a[0]) - order.indexOf(b[0])
    })
)

onMounted(async () => {
  try {
    const res = await api.getCorpusNlp()
    if (res.data.success) data.value = res.data.data
  } catch {}
  loading.value = false
})
</script>

<style scoped>
.corpus-insights {
  width: 100%;
  max-width: 1200px;
  margin: 48px auto 0;
  padding: 0 60px;
}

/* ── Header ──────────────────────────────────────────────── */
.ci-header { margin-bottom: 28px; }

.ci-badge {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: .1em;
  color: #00d4ff;
  background: rgba(0,212,255,.08);
  border: 1px solid rgba(0,212,255,.25);
  padding: 3px 10px;
  border-radius: 2px;
  margin-bottom: 10px;
}

.ci-title {
  font-family: var(--font-serif);
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text);
  margin: 0 0 8px;
  letter-spacing: .02em;
}

.ci-desc {
  font-size: 0.82rem;
  color: var(--text2);
  line-height: 1.6;
  margin: 0;
}
.ci-desc strong { color: var(--text); }

/* ── Loading ─────────────────────────────────────────────── */
.ci-loading { display: flex; gap: 12px; flex-wrap: wrap; }
.ci-skeleton {
  height: 80px; flex: 1; min-width: 140px;
  background: linear-gradient(90deg, var(--bg3) 25%, var(--bg2) 50%, var(--bg3) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite;
  border-radius: var(--radius);
}
@keyframes shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ── Body: two columns ───────────────────────────────────── */
.ci-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 32px;
  align-items: start;
}

.ci-section-label {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: .08em;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.method-tag {
  display: inline-block;
  font-size: 0.6rem;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 2px;
  background: rgba(0,212,255,.10);
  border: 1px solid rgba(0,212,255,.25);
  color: #00d4ff;
  letter-spacing: .06em;
}

/* ── Left: sentiment bars ────────────────────────────────── */
.ci-left {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px 22px;
}

.sentiment-list { display: flex; flex-direction: column; gap: 6px; }

.sent-row {
  display: grid;
  grid-template-columns: 90px 1fr 52px 36px;
  align-items: center;
  gap: 8px;
}

.bp-label {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  color: var(--text2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.bar-track {
  height: 10px;
  border-radius: 2px;
  overflow: hidden;
  display: flex;
  background: var(--bg3);
}

.bar-seg { height: 100%; transition: width .4s ease; }
.bar-pos { background: #22c55e; }
.bar-neu { background: #4b5563; }
.bar-neg { background: #ef4444; }

.bar-pct {
  font-family: var(--font-mono);
  font-size: 0.62rem;
  text-align: right;
  white-space: nowrap;
}
.neg-label { color: #f87171; }
.pct-sub { color: var(--muted); font-size: 0.55rem; }

.vol-label {
  font-family: var(--font-mono);
  font-size: 0.6rem;
  color: var(--muted);
  text-align: right;
}

.sent-legend {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}
.leg-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-family: var(--font-mono);
  font-size: 0.62rem;
  color: var(--muted);
}
.leg-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.leg-dot.pos { background: #22c55e; }
.leg-dot.neu { background: #4b5563; }
.leg-dot.neg { background: #ef4444; }
.leg-note {
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: 0.58rem;
  color: var(--muted);
  opacity: 0.6;
  font-style: italic;
}

/* ── Right: TF-IDF grid ──────────────────────────────────── */
.ci-right {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px 22px;
}

.tfidf-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.bp-card {
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 10px 12px;
  transition: border-color .15s;
}
.bp-card:hover { border-color: rgba(0,212,255,.35); }

.bpc-name {
  display: block;
  font-family: var(--font-mono);
  font-size: 0.63rem;
  font-weight: 700;
  color: #00d4ff;
  letter-spacing: .04em;
  text-transform: uppercase;
  margin-bottom: 7px;
}

.bpc-terms { display: flex; flex-wrap: wrap; gap: 4px; }

.term-chip {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 0.6rem;
  padding: 2px 7px;
  border-radius: 10px;
  background: rgba(0,212,255,.08);
  border: 1px solid rgba(0,212,255,.2);
  color: var(--text2);
  white-space: nowrap;
  cursor: default;
  transition: background .12s, border-color .12s;
}
.term-chip:hover {
  background: rgba(0,212,255,.15);
  border-color: rgba(0,212,255,.4);
  color: var(--text);
}

.tfidf-note {
  font-size: 0.7rem;
  color: var(--muted);
  line-height: 1.5;
  margin: 14px 0 0;
  padding-top: 12px;
  border-top: 1px solid var(--border);
  font-style: italic;
}

/* ── Responsive ──────────────────────────────────────────── */
@media (max-width: 1000px) {
  .corpus-insights { padding: 0 24px; }
  .ci-body { grid-template-columns: 1fr; }
  .tfidf-grid { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 640px) {
  .corpus-insights { padding: 0 16px; }
  .tfidf-grid { grid-template-columns: repeat(2, 1fr); }
  .sent-row { grid-template-columns: 72px 1fr 48px 32px; }
}
</style>
