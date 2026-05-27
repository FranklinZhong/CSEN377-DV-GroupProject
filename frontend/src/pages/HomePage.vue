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
            <span class="t-name">{{ item.name }}</span>
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
        <AnatomyHero />
        <div class="figure-glow"></div>
      </div>
    </div>

    <!-- ── Search Card ── -->
    <div class="search-card">
      <el-tabs v-model="mode" class="search-tabs">
        <el-tab-pane label="🔍  Keyword Search" name="keyword" />
        <el-tab-pane label="🔤  A–Z Browse" name="index" />
        <el-tab-pane label="🩺  By Body Part" name="bodypart" />
      </el-tabs>

      <!-- Keyword Search -->
      <div v-if="mode === 'keyword'" class="keyword-search">
        <div class="input-row">
          <el-autocomplete
            v-model="query"
            :fetch-suggestions="fetchSuggestions"
            placeholder="e.g. metformin, aspirin, ibuprofen…"
            clearable
            size="large"
            style="flex:1"
            @select="onSelect"
          >
            <template #default="{ item }">
              <div class="suggestion-item">
                <span class="drug-name">{{ item.value }}</span>
                <div class="suggestion-tags">
                  <span v-if="item.data_quality === 'full'" class="badge-full">Full Data</span>
                  <span v-if="item.review_count > 0" class="badge-reviews">{{ item.review_count.toLocaleString() }} reviews</span>
                </div>
              </div>
            </template>
          </el-autocomplete>
          <el-button type="primary" size="large" @click="onEnterSearch">Search</el-button>
        </div>

        <div v-if="noResults" class="no-results">
          <span>No exact match. Did you mean:</span>
          <el-button v-for="s in fuzzyResults" :key="s.drug_id"
                     link type="primary" @click="goToDrug(s.drug_id)">
            {{ s.name }}
          </el-button>
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
            <span class="bp-icon">{{ bp.icon }}</span>
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

const router = useRouter()
const mode   = ref<'keyword' | 'index' | 'bodypart'>('keyword')
const query  = ref('')
const noResults   = ref(false)
const showSources = ref(false)
const fuzzyResults  = ref<DrugResult[]>([])
const indexResults  = ref<DrugResult[]>([])
const selectedLetter = ref('')
const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('')

// ── Body Part Browse ──────────────────────────────────────────────────────
const BODY_PARTS = [
  { key: 'heart',        label: 'Heart',        icon: '❤️'  },
  { key: 'lung',         label: 'Lungs',        icon: '🫁'  },
  { key: 'brain',        label: 'Brain',        icon: '🧠'  },
  { key: 'liver',        label: 'Liver',        icon: '🟡'  },
  { key: 'stomach',      label: 'Stomach',      icon: '🫃'  },
  { key: 'kidney',       label: 'Kidneys',      icon: '🫘'  },
  { key: 'immune',       label: 'Immune',       icon: '🛡️'  },
  { key: 'endocrine',    label: 'Endocrine',    icon: '⚗️'  },
  { key: 'muscle',       label: 'Muscles',      icon: '💪'  },
  { key: 'blood',        label: 'Blood',        icon: '🩸'  },
  { key: 'skin',         label: 'Skin',         icon: '✨'  },
  { key: 'vascular',     label: 'Vascular',     icon: '🩺'  },
  { key: 'eye',          label: 'Eyes',         icon: '👁️'  },
  { key: 'ear',          label: 'Ears',         icon: '👂'  },
  { key: 'reproductive', label: 'Reproductive', icon: '🌸'  },
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
const tickerItems = ref([
  { name: 'Aspirin',        use: 'Pain Relief',        reviews: '45.2K', risk: 'low'    },
  { name: 'Metformin',      use: 'Type 2 Diabetes',    reviews: '38.9K', risk: 'medium' },
  { name: 'Ibuprofen',      use: 'Anti-inflammatory',  reviews: '52.1K', risk: 'medium' },
  { name: 'Warfarin',       use: 'Blood Thinner',      reviews: '28.4K', risk: 'high'   },
  { name: 'Lisinopril',     use: 'Hypertension',       reviews: '41.7K', risk: 'medium' },
  { name: 'Sertraline',     use: 'Depression',         reviews: '67.3K', risk: 'medium' },
  { name: 'Atorvastatin',   use: 'High Cholesterol',   reviews: '33.8K', risk: 'low'    },
  { name: 'Omeprazole',     use: 'Acid Reflux',        reviews: '29.6K', risk: 'low'    },
  { name: 'Amoxicillin',    use: 'Antibiotic',         reviews: '19.4K', risk: 'low'    },
  { name: 'Levothyroxine',  use: 'Thyroid',            reviews: '55.1K', risk: 'medium' },
  { name: 'Gabapentin',     use: 'Nerve Pain',         reviews: '78.4K', risk: 'medium' },
  { name: 'Alprazolam',     use: 'Anxiety',            reviews: '58.2K', risk: 'high'   },
  { name: 'Prednisone',     use: 'Anti-inflammatory',  reviews: '35.6K', risk: 'high'   },
  { name: 'Amlodipine',     use: 'Blood Pressure',     reviews: '22.3K', risk: 'low'    },
  { name: 'Zolpidem',       use: 'Insomnia',           reviews: '42.9K', risk: 'medium' },
  { name: 'Duloxetine',     use: 'Depression',         reviews: '61.7K', risk: 'medium' },
  { name: 'Clopidogrel',    use: 'Stroke Prevention',  reviews: '18.5K', risk: 'high'   },
  { name: 'Fluoxetine',     use: 'Antidepressant',     reviews: '74.2K', risk: 'medium' },
])

// ── Quick-access pills ────────────────────────────────────────────────────
const quickDrugs = ref<{ name: string; id: number }[]>([])
const QUICK_NAMES = ['metformin', 'aspirin', 'ibuprofen', 'warfarin', 'lisinopril', 'sertraline']

onMounted(async () => {
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
})

async function fetchSuggestions(q: string, cb: (arr: any[]) => void) {
  if (!q) { cb([]); return }
  try {
    const res = await api.search(q)
    if (res.data.success && Array.isArray(res.data.data))
      cb(res.data.data.map(d => ({ value: d.name, ...d })))
    else cb([])
  } catch { cb([]) }
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
}

/* ── Ticker ─────────────────────────────────────────────────────── */
.ticker-bar {
  width: 100%;
  background: rgba(2, 26, 46, 0.9);
  border-bottom: 1px solid rgba(56,189,248,0.18);
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
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: .1em;
  color: #38bdf8;
  white-space: nowrap;
  border-right: 1px solid rgba(56,189,248,0.2);
  height: 100%;
  background: rgba(14,165,233,0.06);
  flex-shrink: 0;
}

.ticker-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #38bdf8;
  box-shadow: 0 0 8px #38bdf8;
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
  mask-image: linear-gradient(to right, transparent 0%, black 5%, black 95%, transparent 100%);
}

.ticker-track {
  display: flex;
  white-space: nowrap;
  animation: ticker-scroll 55s linear infinite;
  will-change: transform;
}
.ticker-track:hover {
  animation-play-state: paused;
}

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

.t-name {
  font-weight: 700;
  color: #e2e8f0;
  letter-spacing: .01em;
}
.t-use {
  color: #64748b;
}
.t-reviews {
  color: #475569;
  font-size: 0.72rem;
}
.t-risk {
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: .06em;
  text-transform: uppercase;
  padding: 1px 7px;
  border-radius: 8px;
}
.risk-low    { background: rgba(34,197,94,.12);  color: #4ade80; border: 1px solid rgba(34,197,94,.25); }
.risk-medium { background: rgba(251,191,36,.10); color: #fbbf24; border: 1px solid rgba(251,191,36,.2); }
.risk-high   { background: rgba(239,68,68,.10);  color: #f87171; border: 1px solid rgba(239,68,68,.2);  }

.t-sep {
  color: rgba(56,189,248,0.3);
  font-size: 0.9rem;
  padding-left: 16px;
}

/* ── Two-column hero ────────────────────────────────────────────── */
.hero-layout {
  width: 100%;
  max-width: 1200px;
  display: grid;
  grid-template-columns: 1fr 420px;
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
  background: rgba(96,165,250,.10);
  border: 1px solid rgba(96,165,250,.22);
  color: #60a5fa;
  font-size: 0.7rem;
  letter-spacing: .09em;
  text-transform: uppercase;
  padding: 4px 14px;
  border-radius: 20px;
  margin-bottom: 20px;
}

.title {
  font-size: 4rem;
  font-weight: 800;
  letter-spacing: -.03em;
  color: #f1f5f9;
  line-height: 1.05;
  margin: 0 0 16px;
}
.title-accent {
  background: linear-gradient(135deg, #38bdf8, #818cf8);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.subtitle {
  color: #64748b;
  font-size: 0.95rem;
  line-height: 1.7;
  margin: 0 0 32px;
}

/* Stat cards */
.stats-row {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
}

.stat-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid #1e293b;
  border-radius: 12px;
  padding: 14px 20px;
  min-width: 110px;
  position: relative;
  overflow: hidden;
  transition: border-color .2s;
}
.stat-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, #38bdf8, #818cf8);
  opacity: 0.6;
}
.stat-card:hover {
  border-color: rgba(56,189,248,0.3);
}

.stat-value {
  font-size: 1.6rem;
  font-weight: 800;
  color: #f1f5f9;
  letter-spacing: -.02em;
  line-height: 1;
}
.stat-unit {
  font-size: 1rem;
  color: #38bdf8;
}
.stat-label {
  font-size: 0.7rem;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: .06em;
}

/* Right: anatomy figure */
.hero-figure {
  position: relative;
  height: 480px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.figure-glow {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at 50% 40%,
    rgba(14,165,233,0.12) 0%,
    rgba(56,189,248,0.06) 40%,
    transparent 70%);
  pointer-events: none;
  z-index: 0;
}

/* ── Search card ─────────────────────────────────────────────────── */
.search-card {
  width: 100%;
  max-width: 720px;
  background: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 20px;
  padding: 28px 32px;
  z-index: 1;
  box-shadow: 0 20px 60px rgba(0,0,0,.5);
}
.search-tabs { margin-bottom: 20px; }
.input-row { display: flex; gap: 10px; }

.suggestion-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.suggestion-tags {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.badge-full {
  display: inline-block;
  background: rgba(34,197,94,.15);
  border: 1px solid rgba(34,197,94,.4);
  color: #4ade80;
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: .04em;
  padding: 2px 7px;
  border-radius: 10px;
}
.badge-reviews {
  color: #64748b;
  font-size: 0.68rem;
}
.no-results {
  margin-top: 12px;
  color: #94a3b8;
  font-size: 0.88rem;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

/* Quick pills */
.quick-label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: .06em;
  color: #475569;
  margin: 20px 0 10px;
}
.quick-pills { display: flex; flex-wrap: wrap; gap: 8px; }
.pill {
  background: #1e293b;
  border: 1px solid #334155;
  color: #94a3b8;
  padding: 5px 14px;
  border-radius: 20px;
  font-size: 0.82rem;
  cursor: pointer;
  transition: all .15s;
}
.pill:hover {
  background: #0ea5e9;
  border-color: #0ea5e9;
  color: #fff;
}

/* A-Z */
.letter-bar { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 20px; }
.letter-btn {
  width: 34px; height: 34px;
  border: 1px solid #334155;
  background: transparent;
  color: #94a3b8;
  border-radius: 7px;
  cursor: pointer;
  font-weight: 600;
  font-size: .85rem;
  transition: all .15s;
}
.letter-btn:hover, .letter-btn.active {
  background: #0ea5e9; color: #fff; border-color: #0ea5e9;
}
.index-results { max-height: 380px; overflow-y: auto; }
.index-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 12px; border-radius: 8px; cursor: pointer;
  transition: background .15s;
}
.index-item:hover { background: #1e293b; }
.index-item-left { display: flex; align-items: center; gap: 8px; }
.drug-name { font-weight: 500; color: #e2e8f0; }
.drug-use { color: #64748b; font-size: .85rem; max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.empty-msg { color: #64748b; text-align: center; padding: 24px; }

.disclaimer {
  margin-top: 32px;
  font-size: 0.7rem;
  color: #334155;
}

/* ── About the Data button ───────────────────────────────────────── */
.sources-btn {
  margin-top: 20px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  background: transparent;
  border: 1px solid rgba(56,189,248,0.25);
  color: #38bdf8;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: .05em;
  padding: 7px 18px;
  border-radius: 20px;
  cursor: pointer;
  transition: all .18s;
}
.sources-btn:hover {
  background: rgba(56,189,248,0.1);
  border-color: rgba(56,189,248,0.5);
}
.sources-btn-icon {
  font-size: 0.9rem;
  line-height: 1;
}

/* ── Data Sources Modal ──────────────────────────────────────────── */
.modal-fade-enter-active, .modal-fade-leave-active {
  transition: opacity .2s;
}
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
  background: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 20px;
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
  align-items: center;
  margin-bottom: 10px;
}
.modal-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #f1f5f9;
  margin: 0;
}
.modal-close {
  background: transparent;
  border: none;
  color: #475569;
  font-size: 1.1rem;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: color .15s;
}
.modal-close:hover { color: #e2e8f0; }

.modal-desc {
  color: #64748b;
  font-size: 0.85rem;
  line-height: 1.6;
  margin: 0 0 24px;
}

.source-cards {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.source-card {
  display: flex;
  gap: 16px;
  background: #111827;
  border: 1px solid #1e293b;
  border-radius: 14px;
  padding: 18px;
  transition: border-color .15s;
}
.source-card:hover { border-color: rgba(56,189,248,0.2); }

.sc-icon {
  width: 52px;
  height: 52px;
  flex-shrink: 0;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: .04em;
}
.sc-icon.fda   { background: rgba(96,165,250,.15); color: #60a5fa; border: 1px solid rgba(96,165,250,.3); }
.sc-icon.faers { background: rgba(248,113,113,.15); color: #f87171; border: 1px solid rgba(248,113,113,.3); }
.sc-icon.webmd { background: rgba(74,222,128,.15);  color: #4ade80; border: 1px solid rgba(74,222,128,.3); }

.sc-body { flex: 1; min-width: 0; }

.sc-title {
  font-size: 0.88rem;
  font-weight: 700;
  color: #e2e8f0;
  margin: 0 0 6px;
}
.sc-text {
  font-size: 0.79rem;
  color: #64748b;
  line-height: 1.6;
  margin: 0 0 10px;
}
.sc-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}
.sc-tag {
  font-size: 0.66rem;
  font-weight: 600;
  letter-spacing: .04em;
  padding: 2px 8px;
  border-radius: 8px;
  background: rgba(51,65,85,.8);
  color: #94a3b8;
  border: 1px solid #334155;
}
.sc-link {
  font-size: 0.72rem;
  color: #38bdf8;
  text-decoration: none;
  transition: color .15s;
}
.sc-link:hover { color: #7dd3fc; }

.modal-footer-note {
  text-align: center;
  font-size: 0.7rem;
  color: #334155;
  margin: 20px 0 0;
}

/* ── Body Part Browse ────────────────────────────────────────────── */
.bp-hint {
  font-size: 0.78rem;
  color: #64748b;
  margin: 0 0 14px;
}

.bp-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
  margin-bottom: 20px;
}

.bp-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 10px 6px;
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 10px;
  cursor: pointer;
  transition: all .15s;
}
.bp-btn:hover {
  border-color: #4ade80;
  background: rgba(74,222,128,.06);
}
.bp-btn.active {
  border-color: #4ade80;
  background: rgba(74,222,128,.12);
  box-shadow: 0 0 10px rgba(74,222,128,.2);
}

.bp-icon { font-size: 1.25rem; line-height: 1; }
.bp-name {
  font-size: 0.65rem;
  color: #94a3b8;
  font-weight: 500;
  text-align: center;
  white-space: nowrap;
}
.bp-btn.active .bp-name { color: #4ade80; }

.bp-loading { padding: 8px 0; }
.bp-skeleton {
  height: 44px;
  background: linear-gradient(90deg, #1e293b 25%, #253347 50%, #1e293b 75%);
  background-size: 200% 100%;
  animation: bp-shimmer 1.4s infinite;
  border-radius: 8px;
  margin-bottom: 6px;
}
@keyframes bp-shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.bp-result-header {
  font-size: 0.78rem;
  color: #64748b;
  margin-bottom: 10px;
}
.bp-count { color: #4ade80; font-weight: 700; }
.bp-result-header strong { color: #e2e8f0; text-transform: capitalize; }

/* ── Responsive ──────────────────────────────────────────────────── */
@media (max-width: 960px) {
  .hero-layout {
    grid-template-columns: 1fr;
    padding: 36px 24px 16px;
  }
  .hero-figure { display: none; }
  .hero-content { align-items: center; text-align: center; }
  .title { font-size: 3rem; }
  .stats-row { justify-content: center; }
  .search-card { margin: 0 16px; }
}
@media (max-width: 640px) {
  .title { font-size: 2.4rem; }
  .stat-card { min-width: 90px; padding: 10px 14px; }
  .stat-value { font-size: 1.3rem; }
}
</style>
