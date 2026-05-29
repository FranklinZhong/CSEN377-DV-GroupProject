<template>
  <!-- Loading -->
  <div v-if="store.loading.drug" class="dp-loading">
    <div class="dp-loading-bar"></div>
    <p class="dp-loading-text">Loading drug data…</p>
  </div>

  <!-- Error -->
  <div v-else-if="store.errors.drug" class="dp-error">
    <p class="dp-error-code">404</p>
    <p class="dp-error-msg">{{ store.errors.drug }}</p>
    <button class="dp-btn-back" @click="router.push('/')">← Return to Search</button>
  </div>

  <!-- Main -->
  <div v-else-if="store.currentDrug" class="dp">

    <!-- ── Nav ── -->
    <nav class="dp-nav">
      <button class="dp-back" @click="router.push('/')">
        <span class="dp-back-arrow">←</span> Search
      </button>
      <div class="dp-mode-toggle">
        <button
          v-for="m in modes" :key="m.value"
          :class="['dp-mode-btn', `dp-mode-${m.value}`, { active: store.viewMode === m.value }]"
          @click="store.viewMode = m.value"
        >
          <span class="dp-mode-dot" :style="{ background: m.color }"></span>
          {{ m.label }}
          <span class="dp-mode-count">({{ store.loading.benefits ? '…' : m.count }})</span>
        </button>
      </div>
    </nav>

    <!-- ── Split layout ── -->
    <div class="dp-split">

      <!-- LEFT: sticky anatomy panel -->
      <div class="dp-left">
        <div class="dp-drug-header">
          <h1 class="dp-drug-name">{{ store.currentDrug.name }}</h1>
          <p v-if="store.currentDrug.main_use" class="dp-drug-use">
            {{ truncate(store.currentDrug.main_use, 100) }}
          </p>
        </div>

        <div class="dp-anatomy-wrap">
          <AnatomyBody
            :effects="store.anatomyEffects"
            :hovered="store.hoveredPart"
            :view-mode="store.viewMode"
            :benefit-count="store.benefits.length"
            :side-count="store.sideEffects.length"
            :show-toggle="false"
            @update:hovered="store.hoveredPart = $event"
            @update:view-mode="store.viewMode = $event"
          />
        </div>

        <!-- Stats row -->
        <div class="dp-stats">
          <div class="dp-stat">
            <span class="dp-stat-val">{{ store.currentDrug.overall_rating?.toFixed(1) ?? '—' }}</span>
            <span class="dp-stat-key">Rating</span>
          </div>
          <div class="dp-stat-divider"></div>
          <div class="dp-stat">
            <span class="dp-stat-val dp-val-green">
              {{ store.loading.benefits ? '—' : store.benefits.length }}
            </span>
            <span class="dp-stat-key">Benefits</span>
          </div>
          <div class="dp-stat-divider"></div>
          <div class="dp-stat">
            <span class="dp-stat-val dp-val-red">
              {{ store.loading.sideEffects ? '—' : store.sideEffects.length }}
            </span>
            <span class="dp-stat-key">Side Effects</span>
          </div>
        </div>

        <!-- Hover card -->
        <transition name="hover-fade" mode="out-in">
          <div v-if="store.hoveredPart" class="dp-hover-card">
            <p class="dp-hover-region">{{ store.hoveredPart }}</p>
            <div class="dp-hover-list">
              <div
                v-for="e in hoveredEffects.slice(0, 6)"
                :key="e.effect_name"
                class="dp-hover-row"
              >
                <span :class="['dp-dot', e.effect_type === 'benefit' ? 'green' : 'red']"></span>
                <span class="dp-hover-name">{{ e.effect_name }}</span>
                <span :class="['dp-sev', `sev-${e.severity}`]">{{ e.severity }}</span>
              </div>
            </div>
            <p v-if="!hoveredEffects.length" class="dp-hover-empty">No {{ modeLabel }} data for this region.</p>
          </div>
          <div v-else class="dp-hover-card dp-hover-idle">
            <p class="dp-hover-idle-text">Hover an organ to explore</p>
          </div>
        </transition>
      </div>

      <!-- RIGHT: scrollable sections -->
      <div class="dp-right">

        <!-- 01 Official Use -->
        <section class="dp-section" v-if="store.overview?.what_it_treats || store.overview?.key_indications?.length" data-section="01">
          <div class="dp-section-eyebrow">01 — Official Use</div>
          <h2 class="dp-section-heading">What it treats</h2>
          <p v-if="store.overview?.what_it_treats" class="dp-section-body">
            {{ store.overview.what_it_treats }}
          </p>
          <div v-if="store.overview?.key_indications?.length" class="dp-tags">
            <span v-for="ind in store.overview.key_indications" :key="ind" class="dp-tag">
              {{ ind }}
            </span>
          </div>
        </section>

        <!-- 02 Mechanism -->
        <section class="dp-section" v-if="store.overview?.how_it_works" data-section="02">
          <div class="dp-section-eyebrow">02 — Mechanism</div>
          <h2 class="dp-section-heading">How it works</h2>
          <p class="dp-section-body">{{ store.overview.how_it_works }}</p>
          <div v-if="store.overview?.quick_facts" class="dp-facts-strip">
            <span v-if="store.overview.quick_facts.dosage_form" class="dp-fact-item">
              <span class="dp-fact-label">Form</span>
              <span class="dp-fact-val">{{ truncate(store.overview.quick_facts.dosage_form, 40) }}</span>
              <button v-if="store.overview.quick_facts.dosage_form.length > 40" class="dp-fact-expand" @click="dosageModal = true">↗</button>
            </span>
            <span v-if="store.overview.quick_facts.route" class="dp-fact-sep">|</span>
            <span v-if="store.overview.quick_facts.route" class="dp-fact-item">
              <span class="dp-fact-label">Route</span>
              <span class="dp-fact-val">{{ store.overview.quick_facts.route }}</span>
            </span>
            <span v-if="store.overview.quick_facts.rating" class="dp-fact-sep">|</span>
            <span v-if="store.overview.quick_facts.rating" class="dp-fact-item">
              <span class="dp-fact-label">Rating</span>
              <span class="dp-fact-val dp-val-green">{{ store.overview.quick_facts.rating }}/5</span>
            </span>
          </div>
        </section>

        <!-- 03 Body Impact -->
        <section class="dp-section" data-section="03">
          <div class="dp-section-eyebrow">03 — Body Impact</div>
          <h2 class="dp-section-heading">Affected regions</h2>
          <p class="dp-section-sub">Hover a row to highlight the organ on the body map.</p>
          <div class="dp-region-list">
            <template v-if="store.loading.benefits || store.loading.sideEffects">
              <div v-for="i in 5" :key="i" class="dp-region-skeleton"></div>
            </template>
            <template v-else>
              <div
                v-for="e in topAnatomyEffects"
                :key="e.body_part + e.effect_name"
                class="dp-region-row"
                @mouseenter="store.hoveredPart = e.body_part"
                @mouseleave="store.hoveredPart = null"
              >
                <span :class="['dp-dot', e.effect_type === 'benefit' ? 'green' : 'red']"></span>
                <span class="dp-region-part">{{ e.body_part }}</span>
                <span class="dp-region-effect">{{ e.effect_name }}</span>
                <span :class="['dp-sev', `sev-${e.severity}`]">{{ e.severity }}</span>
              </div>
              <p v-if="!topAnatomyEffects.length" class="dp-empty">No data available in this view.</p>
            </template>
          </div>
        </section>

        <!-- 04 Patient Sentiment -->
        <section class="dp-section" data-section="04">
          <div class="dp-section-eyebrow">04 — Patient Sentiment</div>
          <h2 class="dp-section-heading">What patients report</h2>
          <p class="dp-section-sub">Each row is a body region. Bar position shows positive vs negative sentiment balance.</p>
          <TugOfWarChart
            :drug-id="props.drugId"
            :hovered-part="store.hoveredPart"
            @highlight="store.hoveredPart = $event || null"
          />
        </section>

        <!-- 05 Adverse Event Trend -->
        <section class="dp-section" data-section="05">
          <div class="dp-section-eyebrow">05 — FDA Adverse Events</div>
          <h2 class="dp-section-heading">Reported events over time</h2>
          <p class="dp-section-sub">Source: FDA FAERS database. Signal detection via CUSUM method.</p>
          <TrendAnimation :drug-id="props.drugId" :hovered-part="store.hoveredPart" />
        </section>

        <footer class="dp-footer">
          <p>Data sources: FDA FAERS · openFDA Drug Labels · WebMD Patient Reviews</p>
          <p>For educational purposes only · CSEN 377 Data Visualization · SCU Spring 2026</p>
        </footer>
      </div>
    </div>
  </div>

  <Teleport to="body">
    <Transition name="dosage-fade">
      <div v-if="dosageModal" class="dosage-overlay" @click.self="dosageModal = false">
        <div class="dosage-modal">
          <div class="dosage-modal-header">
            <span class="dosage-modal-title">Dosage Form</span>
            <button class="dosage-modal-close" @click="dosageModal = false">✕</button>
          </div>
          <div class="dosage-modal-body">
            <p>{{ store.overview?.quick_facts?.dosage_form?.replace(/[…\.]{1,3}$/, '').trim() }}</p>
            <p class="dosage-modal-note">Source: openFDA Drug Labels (excerpt)</p>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useDrugStore } from '../stores/drugStore'
import AnatomyBody from '../components/AnatomyBody.vue'
import TrendAnimation from '../components/TrendAnimation.vue'
import TugOfWarChart from '../components/TugOfWarChart.vue'

const props  = defineProps<{ drugId: number }>()
const router = useRouter()
const store  = useDrugStore()

const modes = computed(() => [
  { value: 'neutral'     as const, label: 'Overview',     color: '#60a5fa', count: store.benefits.length + store.sideEffects.length },
  { value: 'benefits'    as const, label: 'Benefits',     color: '#22c55e', count: store.benefits.length },
  { value: 'side_effects'as const, label: 'Side Effects', color: '#ff2020', count: store.sideEffects.length },
  { value: 'both'        as const, label: 'Both',         color: '#facc15', count: store.benefits.length + store.sideEffects.length },
])

const modeLabel = computed(() => {
  if (store.viewMode === 'benefits')     return 'benefit'
  if (store.viewMode === 'side_effects') return 'side effect'
  return 'effect'
})

const hoveredEffects = computed(() =>
  store.anatomyEffects.filter(e => e.body_part === store.hoveredPart)
)

const topAnatomyEffects = computed(() => store.anatomyEffects.slice(0, 12))

const dosageModal = ref(false)

async function load(id: number) {
  await store.loadDrug(id)
  store.loadOverview(id)
  await store.loadEffects(id)
  store.loadReviews(id)
  store.viewMode = 'neutral'
}

onMounted(() => load(props.drugId))

function truncate(s: string | null | undefined, n: number) {
  if (!s) return ''
  return s.length > n ? s.slice(0, n).trimEnd() + '…' : s
}
</script>

<style scoped>
/* ── Tokens ── */
.dp, .dp-loading, .dp-error {
  --green:    #22c55e;
  --red:      #ef4444;
  --yellow:   #facc15;
  --blue:     #4a90c4;
  --gold:     #c9a84c;
  --gold-dim: rgba(201,168,76,0.12);
  --bg:       #05080f;
  --bg2:      #0a0e1a;
  --bg3:      #10172a;
  --border:   #1c2540;
  --border2:  #2a3558;
  --text:     #e8e0d0;
  --text2:    #b0a898;
  --muted:    #6b6560;
  --font-serif: 'Playfair Display', Georgia, serif;
  --font-mono:  'IBM Plex Mono', 'Courier New', monospace;
  --font-sans:  'IBM Plex Sans', system-ui, sans-serif;
}

/* ── Base ── */
.dp {
  min-height: 100vh;
  background: var(--bg);
  font-family: var(--font-sans);
  color: var(--text);
  display: flex;
  flex-direction: column;
}

/* ── Loading ── */
.dp-loading {
  height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
  background: var(--bg);
}
.dp-loading-bar {
  width: 200px;
  height: 2px;
  background: var(--border);
  border-radius: 2px;
  overflow: hidden;
  position: relative;
}
.dp-loading-bar::after {
  content: '';
  position: absolute;
  left: -50%;
  width: 50%;
  height: 100%;
  background: var(--gold);
  animation: slide 1.2s ease-in-out infinite;
}
@keyframes slide {
  0%   { left: -50%; }
  100% { left: 150%; }
}
.dp-loading-text {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--muted);
  letter-spacing: 0.08em;
}

/* ── Error ── */
.dp-error {
  height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: var(--bg);
}
.dp-error-code {
  font-family: var(--font-mono);
  font-size: 5rem;
  font-weight: 600;
  color: var(--border);
  line-height: 1;
}
.dp-error-msg { color: var(--muted); font-size: 0.9rem; }
.dp-btn-back {
  margin-top: 16px;
  background: none;
  border: 1px solid var(--border);
  color: var(--text);
  padding: 10px 24px;
  border-radius: 6px;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 0.85rem;
  transition: border-color 0.2s, color 0.2s;
}
.dp-btn-back:hover { border-color: var(--gold); color: var(--gold); }

/* ── Nav ── */
.dp-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 32px;
  border-bottom: 1px solid var(--gold-dim);
  background: rgba(5,8,15,0.92);
  backdrop-filter: blur(12px);
  position: sticky;
  top: 0;
  z-index: 100;
  flex-shrink: 0;
}
.dp-back {
  background: none;
  border: none;
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: 0.78rem;
  cursor: pointer;
  letter-spacing: 0.06em;
  transition: color 0.15s;
  display: flex;
  align-items: center;
  gap: 6px;
}
.dp-back:hover { color: var(--gold); }
.dp-back-arrow { font-size: 1rem; }

.dp-mode-toggle {
  display: flex;
  gap: 4px;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 4px;
}
.dp-mode-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: none;
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: 0.78rem;
  padding: 6px 14px;
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}
.dp-mode-btn:hover { color: var(--text); }
.dp-mode-btn.active {
  background: rgba(255,255,255,0.07);
  color: var(--text);
}
.dp-mode-btn.dp-mode-neutral.active     { color: #60a5fa; box-shadow: inset 0 0 0 1px #1d4ed8; }
.dp-mode-btn.dp-mode-benefits.active    { color: #22c55e; box-shadow: inset 0 0 0 1px #16a34a; }
.dp-mode-btn.dp-mode-side_effects.active{ color: #ff2020; box-shadow: inset 0 0 0 1px #cc0000; }
.dp-mode-btn.dp-mode-both.active        { color: #facc15; box-shadow: inset 0 0 0 1px #b45309; }
.dp-mode-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dp-mode-count { opacity: 0.45; font-size: 0.74rem; }

/* ── Split Layout ── */
.dp-split {
  display: grid;
  grid-template-columns: 420px 1fr;
  height: calc(100vh - 53px);
  overflow: hidden;
}

/* ── Left Panel ── */
.dp-left {
  position: sticky;
  top: 53px;
  height: calc(100vh - 53px);
  overflow-y: auto;
  background: var(--bg2);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  padding: 28px 24px;
  gap: 0;
}
.dp-left::-webkit-scrollbar { width: 4px; }
.dp-left::-webkit-scrollbar-track { background: transparent; }
.dp-left::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

.dp-drug-header { margin-bottom: 20px; }
.dp-drug-name {
  font-family: var(--font-serif);
  font-size: 2.4rem;
  font-weight: 900;
  line-height: 1.1;
  color: var(--text);
  margin: 0 0 8px;
  text-transform: capitalize;
}
.dp-drug-use {
  font-size: 0.82rem;
  color: var(--muted);
  line-height: 1.5;
  font-style: italic;
  margin: 0;
}

.dp-anatomy-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

/* Stats */
.dp-stats {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 16px 0;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  margin: 16px 0;
}
.dp-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
}
.dp-stat-val {
  font-family: var(--font-mono);
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--gold);
  line-height: 1;
}
.dp-stat-key {
  font-family: var(--font-mono);
  font-size: 0.70rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--muted);
}
.dp-stat-divider {
  width: 1px;
  height: 30px;
  background: var(--border);
}
.dp-val-green { color: var(--green); }
.dp-val-red   { color: var(--red); }

/* Hover card — fixed height so anatomy SVG never shifts */
.dp-hover-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px;
  height: 160px;
  overflow-y: auto;
  flex-shrink: 0;
  box-sizing: border-box;
}
.dp-hover-region {
  font-family: var(--font-mono);
  font-size: 0.76rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--blue);
  margin: 0 0 10px;
}
.dp-hover-list { display: flex; flex-direction: column; gap: 5px; }
.dp-hover-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.78rem;
  color: var(--text2);
}
.dp-hover-name { flex: 1; text-transform: capitalize; }
.dp-hover-empty { color: var(--muted); font-size: 0.78rem; font-style: italic; margin: 0; }
.dp-hover-idle { display: flex; align-items: center; justify-content: center; }
.dp-hover-idle-text {
  font-family: var(--font-mono);
  font-size: 0.78rem;
  color: var(--muted);
  letter-spacing: 0.06em;
}

/* Dot */
.dp-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dp-dot.green { background: var(--green); box-shadow: 0 0 5px var(--green); }
.dp-dot.red   { background: var(--red);   box-shadow: 0 0 5px var(--red); }

/* Severity chip */
.dp-sev {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 1px 6px;
  border-radius: 4px;
  flex-shrink: 0;
}
.sev-high   { background: rgba(239,68,68,0.15);  color: #f87171; }
.sev-medium { background: rgba(251,191,36,0.15); color: #fbbf24; }
.sev-low    { background: rgba(100,116,139,0.12); color: #94a3b8; }

/* Transition — opacity only, no translateY (avoids triggering layout shift) */
.hover-fade-enter-active,
.hover-fade-leave-active { transition: opacity 0.12s; }
.hover-fade-enter-from,
.hover-fade-leave-to { opacity: 0; }

/* ── Right Panel ── */
.dp-right {
  overflow-y: auto;
  padding: 0;
}
.dp-right::-webkit-scrollbar { width: 4px; }
.dp-right::-webkit-scrollbar-track { background: transparent; }
.dp-right::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

/* Sections */
.dp-section {
  position: relative;
  overflow: hidden;
  padding: 40px 48px 34px;
  border-bottom: 1px solid var(--border2);
  animation: fadeUp 0.4s ease both;
}
.dp-section:last-of-type { border-bottom: none; }
.dp-section[data-section]::before {
  content: attr(data-section);
  position: absolute;
  right: -0.5rem;
  top: -1.5rem;
  font-family: 'Playfair Display', Georgia, serif;
  font-size: 10rem;
  font-weight: 900;
  line-height: 1;
  color: rgba(201,168,76,0.04);
  pointer-events: none;
  user-select: none;
  z-index: 0;
}
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; }
}
.dp-section:nth-child(1) { animation-delay: 0.05s; }
.dp-section:nth-child(2) { animation-delay: 0.10s; }
.dp-section:nth-child(3) { animation-delay: 0.15s; }
.dp-section:nth-child(4) { animation-delay: 0.20s; }
.dp-section:nth-child(5) { animation-delay: 0.25s; }

.dp-section-eyebrow {
  font-family: var(--font-mono);
  font-size: 0.74rem;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: var(--gold);
  margin-bottom: 10px;
}
.dp-section-heading {
  font-family: var(--font-serif);
  font-size: 1.9rem;
  font-weight: 700;
  color: var(--text);
  margin: 0 0 16px;
  line-height: 1.2;
}
.dp-section-body {
  font-size: 0.9rem;
  line-height: 1.75;
  color: var(--text2);
  max-width: 680px;
  margin: 0 0 18px;
}
.dp-section-sub {
  font-family: var(--font-mono);
  font-size: 0.78rem;
  color: var(--muted);
  margin: -8px 0 20px;
  letter-spacing: 0.04em;
}

/* Tags */
.dp-tags { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px; }
.dp-tag {
  background: var(--gold-dim);
  border: 1px solid rgba(201,168,76,0.25);
  color: var(--gold);
  font-size: 0.80rem;
  padding: 4px 12px;
  border-radius: 20px;
  font-family: var(--font-mono);
  letter-spacing: 0.03em;
  max-width: 280px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Facts */
.dp-facts-strip {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  padding: 10px 0;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  flex-wrap: wrap;
}
.dp-fact-item {
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.dp-fact-sep {
  color: var(--border2);
  font-family: var(--font-mono);
  font-size: 0.9rem;
  user-select: none;
}
.dp-fact-label {
  font-family: var(--font-mono);
  font-size: 0.70rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--muted);
}
.dp-fact-val {
  font-family: var(--font-mono);
  font-size: 0.86rem;
  color: var(--text2);
  text-transform: capitalize;
}
.dp-fact-expand {
  background: none;
  border: none;
  color: var(--gold);
  font-family: var(--font-mono);
  font-size: 0.76rem;
  padding: 0;
  cursor: pointer;
  opacity: 0.7;
}
.dp-fact-expand:hover { opacity: 1; }

/* Dosage form modal */
.dosage-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.7);
  backdrop-filter: blur(4px);
  z-index: 9000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.dosage-modal {
  background: var(--bg3);
  border: 1px solid var(--border2);
  border-radius: 4px;
  width: 100%;
  max-width: 600px;
  box-shadow: 0 24px 64px rgba(0,0,0,0.6);
}
.dosage-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border);
}
.dosage-modal-title {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--gold);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.dosage-modal-close {
  background: none;
  border: none;
  color: var(--muted);
  font-size: 1rem;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: color 0.15s, background 0.15s;
}
.dosage-modal-close:hover { color: var(--text); background: var(--border); }
.dosage-modal-body {
  padding: 20px;
}
.dosage-modal-body p {
  font-size: 0.9rem;
  line-height: 1.8;
  color: var(--text2);
  margin: 0 0 12px;
}
.dosage-modal-note {
  font-size: 0.72rem !important;
  color: var(--muted) !important;
  margin: 0 !important;
  font-style: italic;
}
.dosage-fade-enter-active, .dosage-fade-leave-active { transition: opacity 0.2s; }
.dosage-fade-enter-from, .dosage-fade-leave-to { opacity: 0; }

/* Region list */
.dp-region-list { display: flex; flex-direction: column; gap: 2px; max-width: 700px; }
.dp-region-skeleton {
  height: 40px;
  border-radius: 7px;
  background: linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.07) 50%, rgba(255,255,255,0.04) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s ease infinite;
}
@keyframes shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
.dp-region-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 7px;
  cursor: pointer;
  transition: background 0.12s;
  border: 1px solid transparent;
}
.dp-region-row:hover {
  background: rgba(255,255,255,0.04);
  border-color: var(--border);
}
.dp-region-part {
  font-family: var(--font-mono);
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text2);
  min-width: 96px;
  flex-shrink: 0;
}
.dp-region-effect {
  flex: 1;
  font-size: 0.85rem;
  color: var(--text);
  text-transform: capitalize;
}
.dp-empty {
  color: var(--muted);
  font-size: 0.82rem;
  font-style: italic;
  padding: 12px 0;
}

/* Footer */
.dp-footer {
  padding: 32px 48px;
  border-top: 1px solid var(--border);
  background: var(--bg);
}
.dp-footer p {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  color: var(--muted);
  letter-spacing: 0.05em;
  margin: 3px 0;
  opacity: 0.6;
}

/* ── Responsive ── */
@media (max-width: 1024px) {
  .dp-split { grid-template-columns: 1fr; }
  .dp-left {
    position: static;
    height: auto;
    border-right: none;
    border-bottom: 1px solid var(--border);
  }
  .dp-section { padding: 32px 24px; }
  .dp-footer  { padding: 24px; }
}
</style>
