<template>
  <div class="home">

    <!-- ── Data Ticker ── -->
    <div class="ticker-bar">
      <div class="ticker-badge">
        <span class="ticker-dot"></span>LIVE DATA
      </div>
      <div class="ticker-viewport">
        <div class="ticker-track">
          <span v-for="(item, i) in tickerItems.concat(tickerItems)" :key="i" class="ticker-item">
            <button
              v-if="item.id"
              class="t-name t-name-link"
              @click="goToDrug(item.id!)"
            >{{ item.name }}</button>
            <span v-else class="t-name">{{ item.name }}</span>
            <span class="t-use">{{ item.use }}</span>
            <span class="t-reviews">{{ item.reviews }} reviews</span>
            <span
              class="t-risk"
              :class="`risk-${item.risk}`"
            >{{ item.risk }}</span>
            <span class="t-sep">⬥</span>
          </span>
        </div>
      </div>
    </div>

    <!-- ── Two-column hero ── -->
    <div class="hero-layout">

      <!-- Left: content -->
      <div class="hero-content">
        <div class="hero-badge">CSEN 377 · Data Visualization</div>
        <h1 class="title">Med<span class="title-accent">Insight</span></h1>
        <p class="subtitle">Explore how medications affect the human body.<br>Built on FDA FAERS · WebMD · openFDA.</p>

        <!-- Stat cards -->
        <div class="stats-row">
          <div class="stat-card">
            <span class="stat-value">12K<span class="stat-unit">+</span></span>
            <span class="stat-label">Drugs Indexed</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">4.2M<span class="stat-unit">+</span></span>
            <span class="stat-label">Patient Reviews</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">3</span>
            <span class="stat-label">Visualizations</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">3</span>
            <span class="stat-label">Data Sources</span>
          </div>
        </div>

        <button class="sources-btn" @click="showSources = true">
          <span class="sources-btn-icon">◎</span> About the Data
        </button>
      </div>

      <!-- Right: anatomy figure -->
      <div class="hero-figure">
        <div class="figure-inner">
          <AnatomyHero />
        </div>
        <div class="figure-glow"></div>
      </div>
    </div>

    <!-- ── Search Card ── -->
    <div class="search-card">
      <div class="search-tabs">
        <button :class="['tab-btn', { active: mode === 'keyword' }]" @click="mode = 'keyword'">Keyword Search</button>
        <button :class="['tab-btn', { active: mode === 'index' }]" @click="mode = 'index'">A–Z Browse</button>
        <button :class="['tab-btn', { active: mode === 'bodypart' }]" @click="mode = 'bodypart'">By Body Part</button>
      </div>

      <!-- Keyword Search -->
      <div v-if="mode === 'keyword'" class="keyword-search">
        <div class="input-row">
          <div class="ac-wrap">
            <input
              v-model="query"
              class="ac-input"
              placeholder="e.g. metformin, aspirin, ibuprofen…"
              autocomplete="off"
              @input="onInput"
              @keydown.enter="onEnterSearch"
              @keydown.esc="showDropdown = false"
              @focus="onFocus"
              @blur="onBlur"
            />
            <div v-if="showDropdown && acSuggestions.length" class="ac-dropdown">
              <div
                v-for="item in acSuggestions"
                :key="item.drug_id"
                class="ac-item"
                @mousedown.prevent="onSelect(item)"
              >
                <span class="drug-name">{{ item.name }}</span>
                <div class="suggestion-tags">
                  <span v-if="item.data_quality === 'full'" class="badge-full">Full Data</span>
                  <span v-if="item.review_count > 0" class="badge-reviews">{{ item.review_count.toLocaleString() }} reviews</span>
                </div>
              </div>
            </div>
          </div>
          <button class="search-btn" @click="onEnterSearch">Search</button>
        </div>

        <div v-if="noResults" class="no-results">
          <span>No exact match. Did you mean:</span>
          <button v-for="s in fuzzyResults" :key="s.drug_id"
                  class="fuzz-btn" @click="goToDrug(s.drug_id)">
            {{ s.name }}
          </button>
        </div>

        <div class="quick-label">Popular searches</div>
        <div class="quick-pills">
          <button
            v-for="drug in quickDrugs"
            :key="drug.name"
            class="pill"
            @click="goToDrug(drug.id)"
          >{{ drug.name }}</button>
        </div>
      </div>

      <!-- Body Part Browse -->
      <div v-else-if="mode === 'bodypart'" class="bp-browse">
        <p class="bp-hint">Select a body part to see drugs with known benefits for that area.</p>
        <div class="bp-grid">
          <button
            v-for="bp in BODY_PARTS"
            :key="bp.key"
            class="bp-btn"
            :class="{ active: selectedBodyPart === bp.key }"
            @click="selectBodyPart(bp.key)"
          >
            <span class="bp-name">{{ bp.label }}</span>
          </button>
        </div>

        <div v-if="bpLoading" class="bp-loading">
          <div class="bp-skeleton" v-for="i in 4" :key="i" />
        </div>

        <template v-else-if="selectedBodyPart">
          <div v-if="bpResults.length" class="bp-results">
            <div class="bp-result-header">
              <span class="bp-count">{{ bpResults.length }}</span> drugs with benefits for
              <strong>{{ BODY_PARTS.find(b => b.key === selectedBodyPart)?.label }}</strong>
            </div>
            <div class="index-results">
              <div
                v-for="drug in bpResults"
                :key="drug.drug_id"
                class="index-item"
                @click="goToDrug(drug.drug_id)"
              >
                <div class="index-item-left">
                  <span class="drug-name">{{ drug.name }}</span>
                  <span v-if="drug.data_quality === 'full'" class="badge-full">Full Data</span>
                </div>
                <span class="drug-use">{{ drug.main_use || '—' }}</span>
              </div>
            </div>
          </div>
          <p v-else class="empty-msg">No drugs found for this body part.</p>
        </template>
      </div>

      <!-- A–Z Browse -->
      <div v-else class="az-browse">
        <div class="letter-bar">
          <button
            v-for="l in letters"
            :key="l"
            class="letter-btn"
            :class="{ active: selectedLetter === l }"
            @click="selectLetter(l)"
          >{{ l }}</button>
        </div>
        <div v-if="indexResults.length" class="index-results">
          <div
            v-for="drug in indexResults"
            :key="drug.drug_id"
            class="index-item"
            @click="goToDrug(drug.drug_id)"
          >
            <div class="index-item-left">
              <span class="drug-name">{{ drug.name }}</span>
              <span v-if="drug.data_quality === 'full'" class="badge-full">Full Data</span>
            </div>
            <span class="drug-use">{{ drug.main_use || '—' }}</span>
          </div>
        </div>
        <p v-else-if="selectedLetter" class="empty-msg">
          No drugs found under "{{ selectedLetter }}".
        </p>
      </div>
    </div>

    <!-- ── Body Word Cloud ── -->
    <div class="wordcloud-section">
      <div class="wcs-header">
        <span class="wcs-badge">15 BODY SYSTEMS · TF-IDF · 287K REVIEWS</span>
        <h2 class="wcs-title">Symptom Atlas</h2>
        <p class="wcs-desc">
          Real patient vocabulary, mapped to the human body. Each region surfaces the
          words most distinctive to it — extracted by TF-IDF from 287,256 WebMD reviews.
        </p>
      </div>
      <CorpusWordCloud />
    </div>

    <!-- ── Corpus NLP Insights ── -->
    <CorpusInsights />

    <p class="disclaimer">
      For educational purposes only · Data: FDA FAERS · WebMD · openFDA
    </p>
  </div>

  <!-- ── Data Sources Modal ── -->
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="showSources" class="modal-backdrop" @click.self="showSources = false">
        <div class="modal-box">
          <div class="modal-header">
            <h2 class="modal-title">Data Sources</h2>
            <button class="modal-close" @click="showSources = false">✕</button>
          </div>
          <p class="modal-desc">
            MedInsight combines three public health datasets to give you a multi-angle view of any drug.
          </p>
          <div class="source-cards">

            <div class="source-card">
              <div class="sc-icon fda">FDA</div>
              <div class="sc-body">
                <h3 class="sc-title">openFDA Drug Labels</h3>
                <p class="sc-text">
                  Official prescribing information published by the U.S. Food &amp; Drug Administration.
                  Provides approved indications, mechanism of action, contraindications, and dosage forms
                  for ~8,000 drugs.
                </p>
                <div class="sc-tags">
                  <span class="sc-tag">Indications</span>
                  <span class="sc-tag">Mechanism</span>
                  <span class="sc-tag">Dosage</span>
                </div>
                <a class="sc-link" href="https://open.fda.gov/apis/drug/label/" target="_blank" rel="noopener">open.fda.gov ↗</a>
              </div>
            </div>

            <div class="source-card">
              <div class="sc-icon faers">FAERS</div>
              <div class="sc-body">
                <h3 class="sc-title">FDA FAERS (Adverse Events)</h3>
                <p class="sc-text">
                  The FDA Adverse Event Reporting System collects voluntary reports of drug side effects
                  from patients and healthcare professionals. We use quarterly data to detect unusual
                  spikes via CUSUM statistical analysis.
                </p>
                <div class="sc-tags">
                  <span class="sc-tag">Side Effects</span>
                  <span class="sc-tag">Time Series</span>
                  <span class="sc-tag">Signal Detection</span>
                </div>
                <a class="sc-link" href="https://open.fda.gov/apis/drug/event/" target="_blank" rel="noopener">open.fda.gov/drug/event ↗</a>
              </div>
            </div>

            <div class="source-card">
              <div class="sc-icon webmd">WebMD</div>
              <div class="sc-body">
                <h3 class="sc-title">WebMD Drug Reviews</h3>
                <p class="sc-text">
                  Over 4.2 million patient-written drug reviews scraped from WebMD. Each review is
                  analyzed with VADER sentiment analysis and mapped to body systems, revealing how
                  real patients experience a drug's benefits and side effects.
                </p>
                <div class="sc-tags">
                  <span class="sc-tag">4.2M+ Reviews</span>
                  <span class="sc-tag">Sentiment NLP</span>
                  <span class="sc-tag">Body Mapping</span>
                </div>
                <a class="sc-link" href="https://www.webmd.com/drugs/2/index" target="_blank" rel="noopener">webmd.com/drugs ↗</a>
              </div>
            </div>

          </div>
          <p class="modal-footer-note">
            All data is used for educational and research purposes only.
          </p>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api/client'
import type { DrugResult } from '../api/client'
import AnatomyHero from '../components/AnatomyHero.vue'
import CorpusInsights from '../components/CorpusInsights.vue'
import CorpusWordCloud from '../components/CorpusWordCloud.vue'

const router = useRouter()
const mode   = ref<'keyword' | 'index' | 'bodypart'>('keyword')
const query  = ref('')
const noResults   = ref(false)
const showSources = ref(false)
const fuzzyResults  = ref<DrugResult[]>([])
const indexResults  = ref<DrugResult[]>([])
const selectedLetter = ref('')
const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('')

const acSuggestions = ref<DrugResult[]>([])
const showDropdown  = ref(false)
let acTimer = 0

// ── Body Part Browse ──────────────────────────────────────────────────────
const BODY_PARTS = [
  { key: 'heart',        label: 'Heart'        },
  { key: 'lung',         label: 'Lungs'        },
  { key: 'brain',        label: 'Brain'        },
  { key: 'liver',        label: 'Liver'        },
  { key: 'stomach',      label: 'Stomach'      },
  { key: 'kidney',       label: 'Kidneys'      },
  { key: 'immune',       label: 'Immune'       },
  { key: 'endocrine',    label: 'Endocrine'    },
  { key: 'muscle',       label: 'Muscles'      },
  { key: 'blood',        label: 'Blood'        },
  { key: 'skin',         label: 'Skin'         },
  { key: 'vascular',     label: 'Vascular'     },
  { key: 'eye',          label: 'Eyes'         },
  { key: 'ear',          label: 'Ears'         },
  { key: 'reproductive', label: 'Reproductive' },
]
const selectedBodyPart = ref('')
const bpResults = ref<DrugResult[]>([])
const bpLoading = ref(false)

async function selectBodyPart(part: string) {
  selectedBodyPart.value = part
  bpResults.value = []
  bpLoading.value = true
  try {
    const res = await api.searchByBodyPart(part)
    if (res.data.success) bpResults.value = res.data.data.results
  } catch {}
  bpLoading.value = false
}

// ── Ticker data ───────────────────────────────────────────────────────────
const tickerItems = ref<{ name: string; use: string; reviews: string; risk: string; id: number | null }[]>([
  { name: 'Aspirin',        use: 'Pain Relief',        reviews: '45.2K', risk: 'low',    id: null },
  { name: 'Metformin',      use: 'Type 2 Diabetes',    reviews: '38.9K', risk: 'medium', id: null },
  { name: 'Ibuprofen',      use: 'Anti-inflammatory',  reviews: '52.1K', risk: 'medium', id: null },
  { name: 'Warfarin',       use: 'Blood Thinner',      reviews: '28.4K', risk: 'high',   id: null },
  { name: 'Lisinopril',     use: 'Hypertension',       reviews: '41.7K', risk: 'medium', id: null },
  { name: 'Sertraline',     use: 'Depression',         reviews: '67.3K', risk: 'medium', id: null },
  { name: 'Atorvastatin',   use: 'High Cholesterol',   reviews: '33.8K', risk: 'low',    id: null },
  { name: 'Omeprazole',     use: 'Acid Reflux',        reviews: '29.6K', risk: 'low',    id: null },
  { name: 'Amoxicillin',    use: 'Antibiotic',         reviews: '19.4K', risk: 'low',    id: null },
  { name: 'Levothyroxine',  use: 'Thyroid',            reviews: '55.1K', risk: 'medium', id: null },
  { name: 'Gabapentin',     use: 'Nerve Pain',         reviews: '78.4K', risk: 'medium', id: null },
  { name: 'Alprazolam',     use: 'Anxiety',            reviews: '58.2K', risk: 'high',   id: null },
  { name: 'Prednisone',     use: 'Anti-inflammatory',  reviews: '35.6K', risk: 'high',   id: null },
  { name: 'Amlodipine',     use: 'Blood Pressure',     reviews: '22.3K', risk: 'low',    id: null },
  { name: 'Zolpidem',       use: 'Insomnia',           reviews: '42.9K', risk: 'medium', id: null },
  { name: 'Duloxetine',     use: 'Depression',         reviews: '61.7K', risk: 'medium', id: null },
  { name: 'Clopidogrel',    use: 'Stroke Prevention',  reviews: '18.5K', risk: 'high',   id: null },
  { name: 'Fluoxetine',     use: 'Antidepressant',     reviews: '74.2K', risk: 'medium', id: null },
])

// ── Quick-access pills ────────────────────────────────────────────────────
const quickDrugs = ref<{ name: string; id: number }[]>([])
const QUICK_NAMES = ['metformin', 'aspirin', 'ibuprofen', 'warfarin', 'lisinopril', 'sertraline']

onMounted(async () => {
  // Resolve quick-pill IDs
  const drugs: { name: string; id: number }[] = []
  for (const name of QUICK_NAMES) {
    try {
      const res = await api.search(name)
      if (res.data.success && res.data.data?.length) {
        drugs.push({ name, id: res.data.data[0].drug_id })
      }
    } catch {}
  }
  quickDrugs.value = drugs

  // Resolve ticker IDs in parallel
  await Promise.all(tickerItems.value.map(async (item, idx) => {
    try {
      const res = await api.search(item.name)
      if (res.data.success && res.data.data?.length) {
        tickerItems.value[idx].id = res.data.data[0].drug_id
      }
    } catch {}
  }))
})

async function onInput() {
  if (!query.value) { acSuggestions.value = []; showDropdown.value = false; return }
  clearTimeout(acTimer)
  acTimer = window.setTimeout(async () => {
    try {
      const res = await api.search(query.value)
      if (res.data.success && Array.isArray(res.data.data)) {
        acSuggestions.value = res.data.data.slice(0, 8)
        showDropdown.value = acSuggestions.value.length > 0
      }
    } catch {}
  }, 200)
}

function onFocus() {
  if (acSuggestions.value.length) showDropdown.value = true
}

function onBlur() {
  setTimeout(() => { showDropdown.value = false }, 150)
}

async function onEnterSearch() {
  if (!query.value) return
  noResults.value = false
  fuzzyResults.value = []
  try {
    const res = await api.search(query.value)
    if (res.data.success && res.data.data.length) {
      goToDrug(res.data.data[0].drug_id)
    } else {
      const fuzz = await api.searchFuzzy(query.value)
      fuzzyResults.value = (fuzz.data.data?.suggestions ?? []).slice(0, 5)
      noResults.value = true
    }
  } catch { noResults.value = true }
}

function onSelect(item: any) { goToDrug(item.drug_id) }
function goToDrug(id: number) { router.push({ name: 'drug', params: { id } }) }

async function selectLetter(l: string) {
  selectedLetter.value = l
  indexResults.value = []
  try {
    const res = await api.searchIndex(l)
    if (res.data.success) indexResults.value = res.data.data.results || []
  } catch {}
}
</script>

<style scoped>
.home {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0 0 60px;
  position: relative;
  overflow: hidden;
  background: var(--bg);
  font-family: var(--font-sans);
  color: var(--text);
}

/* ── Ticker ─────────────────────────────────────────────────────── */
.ticker-bar {
  width: 100%;
  background: var(--bg2);
  border-bottom: 1px solid var(--border);
  box-shadow: 0 0 12px rgba(201,168,76,0.06);
  display: flex;
  align-items: center;
  height: 40px;
  overflow: hidden;
  flex-shrink: 0;
}

.ticker-badge {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 0 16px;
  font-family: var(--font-mono);
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: .1em;
  color: var(--gold);
  white-space: nowrap;
  border-right: 1px solid var(--border);
  height: 100%;
  background: var(--gold-dim);
  flex-shrink: 0;
}

.ticker-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--gold);
  box-shadow: 0 0 8px var(--gold);
  animation: dot-blink 1.4s ease-in-out infinite;
}
@keyframes dot-blink {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.3; }
}

.ticker-viewport {
  flex: 1;
  overflow: hidden;
  height: 100%;
  display: flex;
  align-items: center;
  mask-image: linear-gradient(to right, transparent 0%, black 4%, black 96%, transparent 100%);
}

.ticker-track {
  display: flex;
  white-space: nowrap;
  animation: ticker-scroll 55s linear infinite;
  will-change: transform;
}
.ticker-track:hover { animation-play-state: paused; }

@keyframes ticker-scroll {
  0%   { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}

.ticker-item {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 0 24px 0 8px;
  font-size: 0.78rem;
}

.t-name   { font-weight: 700; color: var(--text); letter-spacing: .01em; }
.t-name-link {
  background: none;
  border: none;
  padding: 0;
  font-family: inherit;
  font-size: inherit;
  font-weight: 700;
  letter-spacing: .01em;
  color: var(--gold);
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
  text-decoration-color: rgba(201,168,76,0.4);
  transition: color .12s, text-decoration-color .12s;
}
.t-name-link:hover { color: #e8c97a; text-decoration-color: var(--gold); }
.t-use    { color: var(--text3); }
.t-reviews { color: var(--text3); font-size: 0.72rem; font-family: var(--font-mono); }
.t-risk {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: .06em;
  text-transform: uppercase;
  padding: 1px 7px;
  border-radius: 2px;
}
.risk-low    { background: rgba(34,197,94,.10);  color: #4ade80; border: 1px solid rgba(34,197,94,.2); }
.risk-medium { background: rgba(245,158,11,.10); color: #fbbf24; border: 1px solid rgba(245,158,11,.2); }
.risk-high   { background: rgba(239,68,68,.10);  color: #f87171; border: 1px solid rgba(239,68,68,.2);  }

.t-sep { color: var(--border2); font-size: 0.9rem; padding-left: 16px; }

/* ── Two-column hero ────────────────────────────────────────────── */
.hero-layout {
  width: 100%;
  max-width: 1200px;
  display: grid;
  grid-template-columns: 1fr 320px;
  align-items: center;
  gap: 0;
  padding: 56px 60px 24px;
}

.hero-content {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0;
  z-index: 1;
}

.hero-badge {
  display: inline-block;
  background: var(--gold-dim);
  border: 1px solid rgba(201,168,76,0.3);
  color: var(--gold);
  font-family: var(--font-mono);
  font-size: 0.7rem;
  letter-spacing: .09em;
  text-transform: uppercase;
  padding: 4px 14px;
  border-radius: 2px;
  margin-bottom: 20px;
}

/* Gold hairline above title */
.hero-content::before {
  content: '';
  display: block;
  width: 40px;
  height: 1px;
  background: var(--gold);
  margin-bottom: 16px;
}

.title {
  font-family: var(--font-serif);
  font-size: 4.5rem;
  font-weight: 900;
  color: var(--text);
  line-height: 1.05;
  margin: 0 0 16px;
}
.title-accent { color: var(--gold); }

.subtitle {
  color: var(--text2);
  font-size: 0.95rem;
  line-height: 1.7;
  margin: 0 0 32px;
}

/* Stat cards */
.stats-row { display: flex; gap: 14px; flex-wrap: wrap; }

.stat-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px 20px;
  min-width: 110px;
  position: relative;
  overflow: hidden;
  transition: border-color .2s;
}
.stat-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; bottom: 0;
  width: 2px;
  background: var(--gold);
  opacity: 0.6;
}
.stat-card:hover { border-color: var(--gold); }

.stat-value {
  font-family: var(--font-mono);
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--gold);
  line-height: 1;
}
.stat-unit { font-size: 1rem; color: var(--gold); opacity: 0.7; }
.stat-label {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: .06em;
}

/* Right: anatomy figure */
.hero-figure {
  position: relative;
  height: 520px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.figure-inner {
  width: 100%;
  height: 100%;
  padding-top: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.figure-glow {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at 40% 40%,
    rgba(0,212,255,0.10) 0%,
    rgba(0,140,200,0.04) 40%,
    transparent 70%);
  pointer-events: none;
  z-index: 0;
}

/* ── Search card ─────────────────────────────────────────────────── */
.search-card {
  width: 100%;
  max-width: 720px;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 28px 32px;
  z-index: 1;
  box-shadow: 0 20px 60px rgba(0,0,0,.5);
}

/* Tabs */
.search-tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: 24px;
}
.tab-btn {
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: .08em;
  padding: 8px 20px 10px;
  cursor: pointer;
  transition: color .15s, border-color .15s;
  margin-bottom: -1px;
}
.tab-btn:hover { color: var(--text2); }
.tab-btn.active { color: var(--gold); border-bottom-color: var(--gold); }

/* Autocomplete */
.input-row { display: flex; gap: 10px; }
.ac-wrap { flex: 1; position: relative; }
.ac-input {
  width: 100%;
  height: 44px;
  background: var(--bg3);
  border: 1px solid var(--border2);
  border-radius: var(--radius);
  color: var(--text);
  font-family: var(--font-sans);
  font-size: 0.9rem;
  padding: 0 14px;
  outline: none;
  transition: border-color .15s;
}
.ac-input::placeholder { color: var(--text3); }
.ac-input:focus { border-color: var(--gold); }

.ac-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0; right: 0;
  background: var(--bg3);
  border: 1px solid var(--border2);
  border-radius: var(--radius);
  z-index: 200;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0,0,0,.5);
}
.ac-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: background .1s;
}
.ac-item:hover { background: var(--gold-dim); }

.search-btn {
  height: 44px;
  padding: 0 24px;
  background: var(--gold-dim);
  border: 1px solid var(--gold);
  border-radius: var(--radius);
  color: var(--gold);
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: .06em;
  text-transform: uppercase;
  cursor: pointer;
  transition: background .15s, color .15s;
  white-space: nowrap;
}
.search-btn:hover { background: var(--gold); color: var(--bg); }

.suggestion-tags { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
.badge-full {
  display: inline-block;
  background: rgba(34,197,94,.12);
  border: 1px solid rgba(34,197,94,.3);
  color: #4ade80;
  font-size: 0.65rem;
  font-family: var(--font-mono);
  letter-spacing: .04em;
  padding: 1px 6px;
  border-radius: 2px;
}
.badge-reviews { color: var(--text3); font-size: 0.68rem; font-family: var(--font-mono); }

.no-results {
  margin-top: 12px;
  color: var(--text2);
  font-size: 0.88rem;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}
.fuzz-btn {
  background: none;
  border: none;
  color: var(--gold);
  font-family: var(--font-sans);
  font-size: 0.85rem;
  cursor: pointer;
  padding: 0;
  text-decoration: underline;
  text-underline-offset: 3px;
}
.fuzz-btn:hover { opacity: 0.8; }

/* Quick pills */
.quick-label {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: .08em;
  color: var(--muted);
  margin: 20px 0 10px;
}
.quick-pills { display: flex; flex-wrap: wrap; gap: 8px; }
.pill {
  background: var(--bg3);
  border: 1px solid var(--border2);
  color: var(--text2);
  padding: 5px 14px;
  border-radius: 20px;
  font-size: 0.8rem;
  font-family: var(--font-mono);
  cursor: pointer;
  transition: all .15s;
}
.pill:hover { border-color: var(--gold); color: var(--gold); background: var(--gold-dim); }

/* A-Z */
.letter-bar { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 20px; }
.letter-btn {
  width: 34px; height: 34px;
  border: 1px solid var(--border2);
  background: transparent;
  color: var(--text2);
  border-radius: var(--radius);
  cursor: pointer;
  font-family: var(--font-mono);
  font-weight: 600;
  font-size: .85rem;
  transition: all .15s;
}
.letter-btn:hover { border-color: var(--gold); color: var(--gold); background: var(--gold-dim); }
.letter-btn.active { border-color: var(--gold); color: var(--gold); background: var(--gold-dim); }

.index-results { max-height: 380px; overflow-y: auto; }
.index-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 12px; border-radius: var(--radius); cursor: pointer;
  border-left: 2px solid transparent;
  transition: background .12s, border-color .12s;
}
.index-item:hover { background: var(--bg3); border-left-color: var(--gold); }
.index-item-left { display: flex; align-items: center; gap: 8px; }
.drug-name { font-weight: 500; color: var(--text); }
.drug-use { color: var(--muted); font-size: .85rem; max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.empty-msg { color: var(--muted); text-align: center; padding: 24px; font-style: italic; font-size: 0.85rem; }

/* ── Body Word Cloud Section ─────────────────────────────────── */
.wordcloud-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 28px;
  width: 100%;
  max-width: 1200px;
  padding: 64px 60px 0;
}

.wcs-header {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.wcs-badge {
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
}

.wcs-title {
  font-family: var(--font-serif);
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text);
  margin: 0;
  letter-spacing: .02em;
}

.wcs-desc {
  font-size: 0.82rem;
  color: var(--text2);
  line-height: 1.6;
  margin: 0;
}

.disclaimer {
  margin-top: 32px;
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: var(--muted);
  letter-spacing: .04em;
  opacity: 0.5;
}

/* ── About the Data button ───────────────────────────────────────── */
.sources-btn {
  margin-top: 20px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  background: transparent;
  border: 1px solid rgba(201,168,76,0.3);
  color: var(--gold);
  font-family: var(--font-mono);
  font-size: 0.72rem;
  letter-spacing: .06em;
  text-transform: uppercase;
  padding: 7px 18px;
  border-radius: var(--radius);
  cursor: pointer;
  transition: all .18s;
}
.sources-btn:hover { background: var(--gold-dim); border-color: var(--gold); }
.sources-btn-icon { font-size: 0.9rem; line-height: 1; }

/* ── Data Sources Modal ──────────────────────────────────────────── */
.modal-fade-enter-active, .modal-fade-leave-active { transition: opacity .2s; }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; }

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.72);
  backdrop-filter: blur(6px);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.modal-box {
  background: var(--bg2);
  border: 1px solid var(--border2);
  border-radius: var(--radius);
  padding: 32px;
  max-width: 680px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 40px 80px rgba(0,0,0,.7);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}
.modal-title {
  font-family: var(--font-serif);
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--gold);
  margin: 0;
  letter-spacing: .04em;
}
.modal-close {
  background: transparent;
  border: none;
  color: var(--muted);
  font-size: 1.1rem;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: var(--radius);
  transition: color .15s;
}
.modal-close:hover { color: var(--text); }

.modal-desc {
  color: var(--text2);
  font-size: 0.85rem;
  line-height: 1.6;
  margin: 0 0 24px;
}

.source-cards { display: flex; flex-direction: column; gap: 16px; }

.source-card {
  display: flex;
  gap: 16px;
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 18px;
  transition: border-color .15s;
}
.source-card:hover { border-color: var(--border2); }

.sc-icon {
  width: 52px;
  height: 52px;
  flex-shrink: 0;
  border-radius: var(--radius);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: .04em;
}
.sc-icon.fda   { background: rgba(74,144,196,.15); color: var(--blue); border: 1px solid rgba(74,144,196,.3); border-left: 3px solid var(--blue); }
.sc-icon.faers { background: rgba(239,68,68,.12);  color: #f87171;    border: 1px solid rgba(239,68,68,.25); border-left: 3px solid #ef4444; }
.sc-icon.webmd { background: rgba(34,197,94,.12);  color: #4ade80;    border: 1px solid rgba(34,197,94,.25); border-left: 3px solid #22c55e; }

.sc-body { flex: 1; min-width: 0; }
.sc-title { font-size: 0.88rem; font-weight: 700; color: var(--text); margin: 0 0 6px; }
.sc-text  { font-size: 0.79rem; color: var(--text2); line-height: 1.6; margin: 0 0 10px; }

.sc-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
.sc-tag {
  font-family: var(--font-mono);
  font-size: 0.63rem;
  font-weight: 600;
  letter-spacing: .04em;
  padding: 2px 8px;
  border-radius: 2px;
  background: var(--bg2);
  color: var(--text2);
  border: 1px solid var(--border2);
}
.sc-link {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--gold);
  text-decoration: none;
  transition: opacity .15s;
}
.sc-link:hover { opacity: 0.75; }

.modal-footer-note {
  text-align: center;
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: var(--muted);
  margin: 20px 0 0;
  opacity: 0.6;
}

/* ── Body Part Browse ────────────────────────────────────────────── */
.bp-hint { font-size: 0.78rem; color: var(--muted); margin: 0 0 14px; }

.bp-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 6px;
  margin-bottom: 20px;
}

.bp-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 9px 6px;
  background: var(--bg3);
  border: 1px solid var(--border);
  border-left: 3px solid transparent;
  border-radius: var(--radius);
  cursor: pointer;
  transition: all .12s;
}
.bp-btn:hover { border-color: var(--border2); border-left-color: var(--gold); background: var(--gold-dim); }
.bp-btn.active { border-color: var(--border2); border-left-color: var(--gold); background: var(--gold-dim); }

.bp-name {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: var(--text2);
  font-weight: 500;
  text-align: center;
  white-space: nowrap;
  letter-spacing: .02em;
}
.bp-btn.active .bp-name { color: var(--gold); }

.bp-loading { padding: 8px 0; }
.bp-skeleton {
  height: 44px;
  background: linear-gradient(90deg, var(--bg3) 25%, var(--bg2) 50%, var(--bg3) 75%);
  background-size: 200% 100%;
  animation: bp-shimmer 1.4s infinite;
  border-radius: var(--radius);
  margin-bottom: 6px;
}
@keyframes bp-shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.bp-result-header { font-size: 0.78rem; color: var(--text2); margin-bottom: 10px; }
.bp-count { color: var(--benefit); font-weight: 700; font-family: var(--font-mono); }
.bp-result-header strong { color: var(--text); text-transform: capitalize; }

/* ── Responsive ──────────────────────────────────────────────────── */
@media (max-width: 960px) {
  .hero-layout { grid-template-columns: 1fr; padding: 36px 24px 16px; }
  .hero-figure { display: none; }
  .hero-content { align-items: center; text-align: center; }
  .hero-content::before { margin: 0 auto 16px; }
  .title { font-size: 3rem; }
  .stats-row { justify-content: center; }
  .search-card { margin: 0 16px; }
}
@media (max-width: 640px) {
  .title { font-size: 2.4rem; }
  .stat-card { min-width: 90px; padding: 10px 14px; }
  .stat-value { font-size: 1.3rem; }
  .bp-grid { grid-template-columns: repeat(3, 1fr); }
}
</style>
