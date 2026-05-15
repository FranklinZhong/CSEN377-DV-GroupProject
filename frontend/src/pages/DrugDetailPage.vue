<template>
  <div class="detail-page">
    <!-- Loading -->
    <div v-if="store.loading.drug" class="loading-screen">
      <el-skeleton :rows="4" animated />
    </div>

    <!-- Error -->
    <div v-else-if="store.errors.drug" class="error-screen">
      <el-result icon="error" :title="store.errors.drug" />
      <el-button @click="router.push('/')">← Back to Search</el-button>
    </div>

    <template v-else-if="store.currentDrug">
      <!-- ─── Summary Bar ─── -->
      <header class="summary-bar">
        <el-button class="back-btn" :icon="ArrowLeft" circle plain
                   @click="router.push('/')" />
        <div class="drug-info">
          <h1 class="drug-name">{{ store.currentDrug.name }}</h1>
          <p class="drug-meta">
            <el-tag size="small" type="success" effect="plain">FDA Listed</el-tag>
            <span v-if="store.currentDrug.main_use" class="main-use">
              {{ truncate(store.currentDrug.main_use, 90) }}
            </span>
          </p>
          <p v-if="(store.currentDrug.also_known_as || []).length" class="aliases">
            Also known as: {{ store.currentDrug.also_known_as.slice(0, 4).join(', ') }}
          </p>
        </div>
        <div class="drug-stats">
          <div class="stat">
            <span class="stat-value">
              {{ store.currentDrug.overall_rating?.toFixed(1) ?? '—' }}
            </span>
            <span class="stat-label">Rating</span>
          </div>
          <div class="stat">
            <span class="stat-value" :class="`risk-${store.currentDrug.risk_level}`">
              {{ store.currentDrug.risk_level }}
            </span>
            <span class="stat-label">Risk</span>
          </div>
          <div class="stat" v-if="coverage">
            <span class="stat-value">{{ coverage.benefits }}/{{ coverage.side_effects }}</span>
            <span class="stat-label">Ben/SE</span>
          </div>
        </div>
      </header>

      <!-- ─── Folded Warnings ─── -->
      <div v-if="allWarnings.length" class="warnings-bar">
        <el-popover placement="bottom-start" :width="380" trigger="click">
          <template #reference>
            <el-button text class="warn-toggle">
              ⚠ {{ allWarnings.length }} data advisor{{ allWarnings.length > 1 ? 'ies' : 'y' }}
            </el-button>
          </template>
          <ul class="warn-list">
            <li v-for="(w, i) in allWarnings" :key="i">{{ w }}</li>
          </ul>
        </el-popover>
      </div>

      <!-- ─── Main 3-Column Layout ─── -->
      <div class="main-layout">
        <!-- LEFT: Hovered Organ Card -->
        <aside class="left-panel">
          <p class="panel-label">Hovered region</p>
          <div v-if="store.hoveredPart" class="hover-card">
            <p class="hover-title">{{ store.hoveredPart }}</p>
            <p class="hover-mode">
              <span :class="`mode-chip mode-${store.viewMode}`">
                {{ modeLabel }}
              </span>
            </p>
            <div v-if="hoveredEffects.length" class="hover-effects">
              <div v-for="e in hoveredEffects.slice(0, 6)" :key="e.effect_name"
                   class="effect-row">
                <span :class="['eff-dot', `eff-${e.effect_type}`]"></span>
                <span class="eff-name">{{ e.effect_name }}</span>
                <el-tag size="small" :type="severityTag(e.severity)" effect="plain">
                  {{ e.severity }}
                </el-tag>
              </div>
            </div>
            <p v-else class="no-data">No data for this region in current view.</p>
          </div>
          <div v-else class="hover-card empty">
            <p class="hover-empty-icon">👆</p>
            <p class="no-data">Hover over an organ to see details.</p>
          </div>

          <p class="panel-label" style="margin-top:24px;">Top Effects</p>
          <div class="top-list">
            <div
              v-for="e in topAnatomyEffects"
              :key="`${e.effect_type}-${e.effect_name}`"
              class="top-row"
              @mouseenter="store.hoveredPart = e.body_part"
              @mouseleave="store.hoveredPart = null"
            >
              <span :class="['eff-dot', `eff-${e.effect_type}`]"></span>
              <span class="eff-part">{{ e.body_part }}</span>
              <span class="eff-name">{{ truncate(e.effect_name, 28) }}</span>
            </div>
            <p v-if="!topAnatomyEffects.length" class="no-data">No effects in this view.</p>
          </div>
        </aside>

        <!-- CENTER: Anatomy + ViewMode toggle -->
        <main class="center-panel">
          <AnatomyBody
            :effects="store.anatomyEffects"
            :hovered="store.hoveredPart"
            :view-mode="store.viewMode"
            :benefit-count="store.benefits.length"
            :side-count="store.sideEffects.length"
            :show-toggle="true"
            @update:hovered="store.hoveredPart = $event"
            @update:view-mode="store.viewMode = $event"
          />
        </main>

        <!-- RIGHT: Drug Overview -->
        <aside class="right-panel">
          <p class="panel-section-title">
            <span class="emoji">💊</span> Drug Overview
          </p>

          <div v-if="store.loading.overview" class="overview-loading">
            <el-skeleton :rows="3" animated />
          </div>

          <template v-else-if="store.overview">
            <div class="overview-block" v-if="store.overview.what_it_treats">
              <p class="block-label">What it treats</p>
              <p class="block-body">{{ store.overview.what_it_treats }}</p>
            </div>

            <div class="overview-block" v-if="store.overview.how_it_works">
              <p class="block-label">How it works</p>
              <p class="block-body">{{ store.overview.how_it_works }}</p>
            </div>

            <div class="overview-block" v-if="store.overview.key_indications.length">
              <p class="block-label">Key Indications</p>
              <ul class="indication-list">
                <li v-for="(ind, i) in store.overview.key_indications" :key="i">
                  <span class="indication-bullet">▸</span> {{ ind }}
                </li>
              </ul>
            </div>

            <div class="overview-block quick-facts">
              <p class="block-label">Quick Facts</p>
              <div class="fact-grid">
                <div class="fact" v-if="store.overview.quick_facts.dosage_form">
                  <span class="fact-icon">💊</span>
                  <span class="fact-text">{{ store.overview.quick_facts.dosage_form }}</span>
                </div>
                <div class="fact" v-if="store.overview.quick_facts.route">
                  <span class="fact-icon">🛣</span>
                  <span class="fact-text">{{ store.overview.quick_facts.route }}</span>
                </div>
                <div class="fact" v-if="store.overview.quick_facts.rating !== null">
                  <span class="fact-icon">⭐</span>
                  <span class="fact-text">{{ store.overview.quick_facts.rating }} / 5</span>
                </div>
                <div class="fact">
                  <span class="fact-icon">📚</span>
                  <span class="fact-text">FDA · FAERS · WebMD</span>
                </div>
              </div>
            </div>

            <p v-if="!store.overview.what_it_treats && !store.overview.how_it_works"
               class="no-data" style="text-align:center;padding:20px 0;">
              No FDA overview text available for this drug.
            </p>
          </template>

          <p v-else class="no-data">Overview not available.</p>
        </aside>
      </div>

      <!-- ─── Bottom: Reviews + Trend ─── -->
      <div class="bottom-section">
        <el-tabs v-model="activeTab">
          <el-tab-pane name="reviews">
            <template #label>
              <span class="tab-label"><span class="emoji">💬</span> Patient Reviews</span>
            </template>
            <TugOfWarChart
              :drug-id="props.drugId"
              @highlight="store.hoveredPart = $event"
            />
          </el-tab-pane>

          <el-tab-pane name="trend">
            <template #label>
              <span class="tab-label"><span class="emoji">📈</span> Timeline (FAERS)</span>
            </template>
            <TrendAnimation :drug-id="props.drugId" />
          </el-tab-pane>
        </el-tabs>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { useDrugStore } from '../stores/drugStore'
import AnatomyBody from '../components/AnatomyBody.vue'
import TrendAnimation from '../components/TrendAnimation.vue'
import TugOfWarChart from '../components/TugOfWarChart.vue'

const props = defineProps<{ drugId: number }>()
const router = useRouter()
const store  = useDrugStore()
const activeTab = ref('reviews')

const allWarnings = computed(() => [
  ...(store.warnings.drug || []),
  ...(store.warnings.overview || []),
  ...(store.warnings.benefits || []),
  ...(store.warnings.sideEffects || []),
])

const hoveredEffects = computed(() =>
  store.anatomyEffects.filter(e => e.body_part === store.hoveredPart)
)

const topAnatomyEffects = computed(() =>
  store.anatomyEffects.slice(0, 10)
)

const coverage = computed(() => store.currentDrug?.data_coverage)

const modeLabel = computed(() => {
  switch (store.viewMode) {
    case 'benefits':     return 'Benefit'
    case 'side_effects': return 'Side effect'
    case 'both':         return 'Both'
  }
})

async function load(id: number) {
  await store.loadDrug(id)
  store.loadOverview(id)
  await store.loadEffects(id)
  store.loadReviews(id)

  // 自动 fallback：如果没有 benefits 数据，默认切到 side_effects
  if (store.benefits.length === 0 && store.sideEffects.length > 0) {
    store.viewMode = 'side_effects'
  } else if (store.benefits.length > 0) {
    store.viewMode = 'benefits'
  }
}

onMounted(() => load(props.drugId))

function severityTag(s: string) {
  if (s === 'high')   return 'danger'
  if (s === 'medium') return 'warning'
  return 'info'
}

function truncate(s: string, n: number) {
  if (!s) return ''
  return s.length > n ? s.slice(0, n).trimEnd() + '…' : s
}
</script>

<style scoped>
.detail-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #0b1224 0%, #0a0e1c 100%);
}
.loading-screen, .error-screen {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
  gap: 20px;
}

/* ── Summary Bar ── */
.summary-bar {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 18px 28px;
  background: linear-gradient(180deg, rgba(17,24,39,0.95), rgba(17,24,39,0.7));
  border-bottom: 1px solid #1e293b;
  backdrop-filter: blur(8px);
}
.back-btn { flex-shrink: 0; }
.drug-info { flex: 1; min-width: 0; }
.drug-name {
  font-size: 1.7rem;
  font-weight: 800;
  background: linear-gradient(135deg, #f1f5f9 0%, #94a3b8 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0;
}
.drug-meta {
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.main-use { color: #94a3b8; font-size: 0.88rem; }
.aliases  { color: #64748b; font-size: 0.78rem; margin-top: 4px; }
.drug-stats { display: flex; gap: 22px; padding-right: 8px; }
.stat { display: flex; flex-direction: column; align-items: center; }
.stat-value { font-size: 1.35rem; font-weight: 700; color: #f1f5f9; }
.stat-label {
  font-size: 0.68rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-top: 2px;
}
.risk-high { color: #ef4444; }
.risk-moderate { color: #f59e0b; }
.risk-low { color: #22c55e; }
.risk-unknown { color: #94a3b8; }

/* ── Warnings ── */
.warnings-bar {
  padding: 0 28px;
  background: #0d1424;
  border-bottom: 1px solid #1e293b;
}
.warn-toggle {
  color: #fbbf24;
  font-size: 0.78rem;
  padding: 6px 0;
}
.warn-list {
  margin: 0;
  padding-left: 18px;
  font-size: 0.82rem;
  color: #94a3b8;
}
.warn-list li { margin-bottom: 6px; }

/* ── Main Layout ── */
.main-layout {
  display: grid;
  grid-template-columns: 240px 1fr 300px;
  gap: 0;
  min-height: 560px;
}
@media (max-width: 1100px) {
  .main-layout {
    grid-template-columns: 1fr;
  }
  .left-panel, .right-panel { border: none !important; }
}

.left-panel, .right-panel {
  padding: 22px 18px;
  background: #0d1424;
  border-right: 1px solid #1e293b;
}
.right-panel {
  border-right: none;
  border-left: 1px solid #1e293b;
  background: linear-gradient(180deg, #0d1424 0%, #0a0f1e 100%);
}

.center-panel {
  padding: 28px 24px;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  background: radial-gradient(ellipse at center,
              rgba(96,165,250,0.04) 0%,
              transparent 70%);
}

.panel-label, .panel-section-title {
  font-size: 0.7rem;
  text-transform: uppercase;
  color: #475569;
  margin-bottom: 14px;
  letter-spacing: 0.08em;
  font-weight: 600;
}
.panel-section-title {
  font-size: 0.78rem;
  color: #cbd5e1;
  display: flex;
  align-items: center;
  gap: 8px;
}
.emoji { font-style: normal; }

/* Hover Card */
.hover-card {
  background: #111827;
  border: 1px solid #1e293b;
  border-radius: 12px;
  padding: 14px;
  min-height: 80px;
}
.hover-card.empty {
  text-align: center;
}
.hover-empty-icon {
  font-size: 1.6rem;
  margin: 6px 0;
}
.hover-title {
  font-weight: 700;
  color: #f1f5f9;
  text-transform: capitalize;
  font-size: 1rem;
}
.hover-mode {
  margin-top: 4px;
  margin-bottom: 10px;
}
.mode-chip {
  display: inline-block;
  font-size: 0.65rem;
  padding: 2px 8px;
  border-radius: 10px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 700;
}
.mode-chip.mode-benefits     { background: rgba(74,222,128,0.15);  color: #4ade80; }
.mode-chip.mode-side_effects { background: rgba(248,113,113,0.15); color: #f87171; }
.mode-chip.mode-both         { background: rgba(250,204,21,0.15);  color: #facc15; }

.hover-effects {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.effect-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.78rem;
  padding: 4px 0;
  border-bottom: 1px solid #1e293b;
}
.effect-row:last-child { border-bottom: none; }
.eff-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}
.eff-benefit     { background: #4ade80; box-shadow: 0 0 6px #4ade80; }
.eff-side_effect { background: #f87171; box-shadow: 0 0 6px #f87171; }
.eff-name {
  flex: 1;
  color: #cbd5e1;
  text-transform: capitalize;
  font-size: 0.78rem;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.eff-part {
  color: #94a3b8;
  text-transform: capitalize;
  font-size: 0.72rem;
  min-width: 58px;
}
.no-data {
  color: #475569;
  font-size: 0.78rem;
  font-style: italic;
}

.top-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.top-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: background .15s;
}
.top-row:hover { background: rgba(96,165,250,0.06); }

/* ── Right Panel — Drug Overview ── */
.overview-block {
  margin-bottom: 18px;
  padding-bottom: 14px;
  border-bottom: 1px solid #1e293b;
}
.overview-block:last-of-type { border-bottom: none; }
.block-label {
  font-size: 0.7rem;
  text-transform: uppercase;
  color: #64748b;
  letter-spacing: 0.06em;
  margin-bottom: 8px;
  font-weight: 600;
}
.block-body {
  color: #cbd5e1;
  font-size: 0.85rem;
  line-height: 1.55;
}
.indication-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.indication-list li {
  font-size: 0.82rem;
  color: #cbd5e1;
  line-height: 1.45;
}
.indication-bullet {
  color: #60a5fa;
  margin-right: 4px;
}
.fact-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.fact {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #111827;
  padding: 8px 10px;
  border-radius: 8px;
  font-size: 0.76rem;
  color: #cbd5e1;
}
.fact-icon { font-size: 0.92rem; }
.fact-text {
  text-transform: capitalize;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.overview-loading { padding: 12px 0; }

/* ── Bottom Section ── */
.bottom-section {
  padding: 24px 28px;
  border-top: 1px solid #1e293b;
  background: #0a0f1e;
}
.tab-label {
  display: flex;
  align-items: center;
  gap: 6px;
}
</style>
