<template>
  <div class="home">

    <!-- Anatomical hero illustration (v3.5) -->
    <div class="hero-figure" aria-hidden="true">
      <AnatomyHero />
    </div>
    <div class="hero-glow"></div>

    <!-- Hero -->
    <div class="hero">
      <div class="hero-badge">CSEN 377 · Data Visualization</div>
      <h1 class="title">Med<span class="title-accent">Insight</span></h1>
      <p class="subtitle">Visualize how drugs affect your body<br>Search any medication to explore its impact</p>
    </div>

    <!-- Search Card -->
    <div class="search-card">
      <el-tabs v-model="mode" class="search-tabs">
        <el-tab-pane label="🔍  Keyword Search" name="keyword" />
        <el-tab-pane label="🔤  A–Z Browse" name="index" />
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
                <el-tag size="small" :type="riskColor(item.risk_level)" effect="dark">
                  {{ item.risk_level }}
                </el-tag>
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

        <!-- Quick access -->
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
            <span class="drug-name">{{ drug.name }}</span>
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
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api/client'
import type { DrugResult } from '../api/client'
import AnatomyHero from '../components/AnatomyHero.vue'

const router = useRouter()
const mode   = ref<'keyword' | 'index'>('keyword')
const query  = ref('')
const noResults   = ref(false)
const fuzzyResults  = ref<DrugResult[]>([])
const indexResults  = ref<DrugResult[]>([])
const selectedLetter = ref('')
const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('')

// Quick-access pills — resolve IDs from API on mount
const quickDrugs = ref<{ name: string; id: number }[]>([])
const QUICK_NAMES = ['metformin', 'aspirin', 'ibuprofen', 'warfarin', 'lisinopril', 'sertraline']

onMounted(async () => {
  const results = await Promise.allSettled(
    QUICK_NAMES.map(n => api.search(n))
  )
  quickDrugs.value = results
    .map((r, i) => {
      if (r.status === 'fulfilled' && r.value.data.data?.length) {
        return { name: QUICK_NAMES[i], id: r.value.data.data[0].drug_id }
      }
      return null
    })
    .filter(Boolean) as { name: string; id: number }[]
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
      fuzzyResults.value = fuzz.data.data.suggestions.slice(0, 5)
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

function riskColor(risk: string) {
  if (risk === 'high') return 'danger'
  if (risk === 'moderate') return 'warning'
  return 'success'
}
</script>

<style scoped>
.home {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 48px 20px 60px;
  position: relative;
  overflow: hidden;
}

/* ── Hero anatomy figure (v3.5) ── */
.hero-figure {
  position: absolute;
  top: 60px;
  right: 2vw;
  width: clamp(280px, 30vw, 460px);
  height: auto;
  opacity: 0.55;
  pointer-events: none;
  filter: blur(0.3px);
  z-index: 0;
}
.hero-glow {
  position: absolute;
  top: 120px;
  right: 6vw;
  width: 380px;
  height: 380px;
  background: radial-gradient(circle at center,
              rgba(96,165,250,0.18) 0%,
              rgba(167,139,250,0.10) 35%,
              transparent 70%);
  filter: blur(28px);
  pointer-events: none;
  z-index: 0;
}
@media (max-width: 900px) {
  .hero-figure, .hero-glow { display: none; }
}

/* ── Hero ── */
.hero {
  text-align: center;
  margin-bottom: 40px;
  z-index: 1;
}
.hero-badge {
  display: inline-block;
  background: rgba(96,165,250,.12);
  border: 1px solid rgba(96,165,250,.25);
  color: #60a5fa;
  font-size: 0.72rem;
  letter-spacing: .08em;
  text-transform: uppercase;
  padding: 4px 14px;
  border-radius: 20px;
  margin-bottom: 18px;
}
.title {
  font-size: 3.4rem;
  font-weight: 800;
  letter-spacing: -.02em;
  color: #f1f5f9;
  line-height: 1.1;
}
.title-accent {
  background: linear-gradient(135deg, #60a5fa, #a78bfa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.subtitle {
  color: #64748b;
  margin-top: 12px;
  font-size: 1rem;
  line-height: 1.7;
}

/* ── Search card ── */
.search-card {
  width: 100%;
  max-width: 680px;
  background: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 20px;
  padding: 28px 32px;
  z-index: 1;
  box-shadow: 0 20px 60px rgba(0,0,0,.4);
}
.search-tabs { margin-bottom: 20px; }
.input-row { display: flex; gap: 10px; }
.suggestion-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
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
  font-size: 0.72rem;
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
  background: #3b82f6;
  border-color: #3b82f6;
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
  background: #3b82f6; color: #fff; border-color: #3b82f6;
}
.index-results { max-height: 380px; overflow-y: auto; }
.index-item {
  display: flex; justify-content: space-between;
  padding: 10px 12px; border-radius: 8px; cursor: pointer;
  transition: background .15s;
}
.index-item:hover { background: #1e293b; }
.drug-name { font-weight: 500; }
.drug-use { color: #64748b; font-size: .85rem; }
.empty-msg { color: #64748b; text-align: center; padding: 24px; }

.disclaimer {
  margin-top: 28px;
  font-size: 0.7rem;
  color: #334155;
  z-index: 1;
}
</style>
