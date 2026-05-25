<!--
  TrendAnimation.vue — Vis 2  FAERS 季度时间轴动画  (Sprint 3 完整版)

  功能:
  ├── 热力图总览 (body_part × quarter, YlOrRd 色阶, 信号列标红边)
  ├── D3 时间轴 scrubber (圆点 + 蓝色播放游标)
  ├── 当前帧身体系统亮度条 (带动画过渡)
  ├── 播放 / 暂停 / 步进 / 速度 / 跳转
  ├── CUSUM 信号标注 ⚠，可点击跳转
  └── 键盘：Space 播放, ← → 步进
-->
<template>
  <div class="trend-container" ref="containerRef">

    <!-- ── 标题 + 控制 ── -->
    <div class="trend-header">
      <h3 class="vis-title">
        <span class="emoji">📈</span> Side Effect Trend (FAERS)
      </h3>
      <div class="controls">
        <el-button-group size="small">
          <el-button :icon="CaretLeft"  plain @click="stepBack"
                     :disabled="!quarters.length || quarterIdx === 0" />
          <el-button :icon="isPlaying ? VideoPause : VideoPlay"
                     @click="togglePlay" :disabled="!quarters.length" />
          <el-button :icon="CaretRight" plain @click="stepForward"
                     :disabled="!quarters.length || quarterIdx >= quarters.length - 1" />
        </el-button-group>

        <el-select v-model="speed" size="small" style="width:80px" @change="onSpeedChange">
          <el-option label="0.5×" :value="600" />
          <el-option label="1×"   :value="300" />
          <el-option label="2×"   :value="150" />
        </el-select>

        <el-button :icon="Refresh" size="small" plain @click="reset" />
        <span class="quarter-label">{{ currentQuarter }}</span>
      </div>
    </div>

    <!-- ── Narrative ── -->
    <Transition name="fade">
      <div class="narrative" v-if="narrativeText" :key="narrativeText">
        <el-icon><InfoFilled /></el-icon>
        <span>{{ narrativeText }}</span>
      </div>
    </Transition>

    <!-- ── States ── -->
    <div v-if="loading" class="trend-placeholder">
      <el-skeleton :rows="3" animated />
      <p class="loading-note">
        Querying FDA FAERS API — first load may take up to 30 s; results cached for 7 days.
      </p>
    </div>
    <div v-else-if="error" class="trend-placeholder">
      <el-alert :title="error" type="warning" :closable="false" show-icon />
    </div>
    <div v-else-if="!quarters.length" class="trend-placeholder">
      <p style="color:#64748b;font-size:0.85rem">
        No FAERS trend data available for this drug.
      </p>
    </div>

    <template v-else>

      <!-- ── 热力图总览 ── -->
      <div class="section-label">Report Intensity Overview</div>
      <div class="heatmap-wrap" ref="heatmapRef"></div>

      <!-- ── D3 时间轴 scrubber ── -->
      <div class="timeline-wrap" ref="timelineRef"></div>

      <!-- ── 当前帧身体系统条 ── -->
      <div class="section-label" style="margin-top:14px">
        Active Systems · {{ currentQuarter }}
      </div>
      <div class="body-bars">
        <TransitionGroup name="bar-list" tag="div">
          <div v-for="row in currentFrame" :key="row.body_part" class="bar-row">
            <span class="bar-label">{{ row.body_part }}</span>
            <div class="bar-track">
              <div class="bar-fill"
                   :style="{ width: toPercent(row.normalized_frequency),
                             background: barGradient(row) }"
              />
            </div>
            <span class="bar-count">{{ row.report_count.toLocaleString() }}</span>
            <el-tag v-if="row.signal_flag" size="small" type="danger" effect="dark">⚠ spike</el-tag>
            <span v-else class="conf-pill" :class="`conf-${row.confidence}`">
              {{ row.confidence }}
            </span>
          </div>
        </TransitionGroup>
        <p v-if="!currentFrame.length" class="no-data-sm">
          No reports in {{ currentQuarter }}.
        </p>
      </div>

      <!-- ── CUSUM 信号事件列表 ── -->
      <div v-if="signalEvents.length" class="signal-list">
        <p class="signal-title">
          CUSUM Signal Events ({{ signalEvents.length }})
          <span class="signal-hint">· click to jump</span>
        </p>
        <div
          v-for="ev in signalEvents"
          :key="`${ev.quarter}-${ev.body_part}`"
          class="signal-item"
          @click="goToQuarter(ev.quarter)"
        >
          <el-tag type="danger" size="small">{{ ev.quarter }}</el-tag>
          <span class="signal-body">{{ ev.body_part }}</span>
          <span v-if="ev.increase_pct !== null" class="signal-pct">
            ↑{{ ev.increase_pct }}% vs prev quarter
          </span>
        </div>
      </div>

      <p class="data-note">
        Source: FDA FAERS API · CUSUM ⚠ = statistically unusual quarterly spike ·
        Keyboard: <kbd>Space</kbd> play/pause · <kbd>←</kbd><kbd>→</kbd> step
      </p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import {
  InfoFilled, VideoPlay, VideoPause,
  Refresh, CaretLeft, CaretRight,
} from '@element-plus/icons-vue'
import * as d3 from 'd3'
import { api } from '../api/client'
import type { TrendPoint } from '../api/client'

const props = defineProps<{ drugId: number }>()

// ── State ──────────────────────────────────────────────────────────────────
const loading      = ref(false)
const error        = ref('')
const timeline     = ref<TrendPoint[]>([])
const signalEvents = ref<any[]>([])
const quarterIdx   = ref(0)
const isPlaying    = ref(false)
const speed        = ref(300)   // ms per step

const containerRef = ref<HTMLElement | null>(null)
const timelineRef  = ref<HTMLElement | null>(null)
const heatmapRef   = ref<HTMLElement | null>(null)

// D3 selection references for incremental updates
let tsvg: d3.Selection<SVGSVGElement, unknown, null, undefined> | null = null
let hsvg: d3.Selection<SVGSVGElement, unknown, null, undefined> | null = null
let tScale: d3.ScalePoint<string> | null = null
let tPlayhead: d3.Selection<SVGLineElement, unknown, null, undefined> | null = null
let hPlayhead: d3.Selection<SVGLineElement, unknown, null, undefined> | null = null

// Heatmap geometry (stored for incremental updates)
let hmLabelW = 70
let hmCellW  = 4

let playTimer: ReturnType<typeof setInterval> | null = null

// ── Computed ────────────────────────────────────────────────────────────────
const quarters = computed(() =>
  [...new Set(timeline.value.map(p => p.quarter))].sort()
)

const currentQuarter = computed(() =>
  quarters.value[quarterIdx.value] ?? '—'
)

const currentFrame = computed<TrendPoint[]>(() => {
  const q = currentQuarter.value
  return timeline.value
    .filter(p => p.quarter === q && p.report_count > 0)
    .sort((a, b) => b.report_count - a.report_count)
    .slice(0, 10)
})

const narrativeText = computed(() => {
  const frame = currentFrame.value
  if (!frame.length) return ''
  const signals = frame.filter(p => p.signal_flag)
  const top     = frame[0]
  if (signals.length) {
    return `In ${currentQuarter.value}, ${signals[0].body_part} reports showed a statistically significant spike.`
  }
  return `In ${currentQuarter.value}, top affected system: ${top.body_part} (${top.report_count.toLocaleString()} reports).`
})

const topBodyParts = computed(() => {
  const totals: Record<string, number> = {}
  for (const p of timeline.value)
    totals[p.body_part] = (totals[p.body_part] ?? 0) + p.report_count
  return Object.entries(totals)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([k]) => k)
})

// ── Data loading ────────────────────────────────────────────────────────────
async function load(id: number) {
  loading.value     = true
  error.value       = ''
  timeline.value    = []
  signalEvents.value = []
  quarterIdx.value  = 0
  tsvg = hsvg = tPlayhead = hPlayhead = tScale = null
  stopPlay()

  try {
    const res = await api.getTrend(id)
    if (res.data.success) {
      timeline.value     = res.data.data.timeline     ?? []
      signalEvents.value = res.data.data.signal_events ?? []
      await nextTick()
      buildVisualizations()
    } else {
      error.value = 'Trend data unavailable for this drug.'
    }
  } catch {
    error.value = 'Failed to fetch trend data from FDA FAERS.'
  } finally {
    loading.value = false
  }
}

watch(() => props.drugId, load, { immediate: true })

// ── D3 visualizations ──────────────────────────────────────────────────────
function buildVisualizations() {
  buildHeatmap()
  buildTimeline()
}

function buildHeatmap() {
  const el = heatmapRef.value
  if (!el || !timeline.value.length) return
  el.innerHTML = ''

  const parts  = topBodyParts.value
  const qs     = quarters.value
  if (!parts.length || !qs.length) return

  hmLabelW = 72
  const W     = Math.max(el.clientWidth || 600, 300)
  const cellH = 18
  hmCellW     = Math.max(2, (W - hmLabelW - 10) / qs.length)
  const H     = parts.length * cellH + 24

  const signalQtrs = new Set(signalEvents.value.map((e: any) => e.quarter))
  const color = d3.scaleSequential(d3.interpolateYlOrRd).domain([0, 1])

  hsvg = d3.select(el).append('svg')
    .attr('width', W).attr('height', H)

  // Cells
  parts.forEach((part, row) => {
    qs.forEach((q, col) => {
      const cell  = timeline.value.find(p => p.body_part === part && p.quarter === q)
      const freq  = cell?.normalized_frequency ?? 0
      const isSig = cell?.signal_flag ?? false

      hsvg!.append('rect')
        .attr('x',      hmLabelW + col * hmCellW)
        .attr('y',      row * cellH + 2)
        .attr('width',  Math.max(1, hmCellW - 1))
        .attr('height', cellH - 3)
        .attr('fill',   freq > 0 ? color(freq) : '#0f172a')
        .attr('stroke', isSig ? '#ef4444' : 'none')
        .attr('stroke-width', 1)
        .attr('rx', 1)
    })

    hsvg!.append('text')
      .attr('x', hmLabelW - 5)
      .attr('y', row * cellH + cellH / 2 + 4)
      .attr('text-anchor', 'end')
      .attr('fill', '#64748b')
      .attr('font-size', 9)
      .text(part.length > 9 ? part.slice(0, 8) + '…' : part)
  })

  // Year labels (Q1 only)
  qs.forEach((q, col) => {
    if (q.endsWith('Q1')) {
      hsvg!.append('text')
        .attr('x', hmLabelW + (col + 0.5) * hmCellW)
        .attr('y', H - 2)
        .attr('text-anchor', 'middle')
        .attr('fill', '#475569')
        .attr('font-size', 9)
        .text(q.slice(0, 4))
    }
  })

  // Playhead (semi-transparent vertical band)
  const qIdx = qs.indexOf(currentQuarter.value)
  hPlayhead = hsvg!.append('line')
    .attr('x1', hmLabelW + (qIdx + 0.5) * hmCellW)
    .attr('x2', hmLabelW + (qIdx + 0.5) * hmCellW)
    .attr('y1', 0)
    .attr('y2', parts.length * cellH + 2)
    .attr('stroke', '#60a5fa')
    .attr('stroke-width', Math.max(2, hmCellW - 1))
    .attr('opacity', 0.22)
    .attr('pointer-events', 'none')
}

function buildTimeline() {
  const el = timelineRef.value
  if (!el || !quarters.value.length) return
  el.innerHTML = ''

  const W  = Math.max(el.clientWidth || 600, 300)
  const H  = 60
  const mL = hmLabelW
  const mR = 10

  tsvg = d3.select(el).append('svg').attr('width', W).attr('height', H)
  const g = tsvg.append('g').attr('transform', `translate(${mL},0)`)

  tScale = d3.scalePoint<string>()
    .domain(quarters.value)
    .range([0, W - mL - mR])
    .padding(0.1)

  const signalQtrs = new Set(signalEvents.value.map((e: any) => e.quarter))

  // Track
  g.append('line')
    .attr('x1', 0).attr('x2', W - mL - mR)
    .attr('y1', 30).attr('y2', 30)
    .attr('stroke', '#1e293b').attr('stroke-width', 3)

  // Dots (data-bound)
  g.selectAll<SVGCircleElement, string>('.q-dot')
    .data(quarters.value)
    .enter().append('circle')
    .attr('class', 'q-dot')
    .attr('cx',    d => tScale!(d) ?? 0)
    .attr('cy',    30)
    .attr('r',     d => signalQtrs.has(d) ? 6 : 3)
    .attr('fill',  d => signalQtrs.has(d) ? '#ef4444' : '#334155')
    .attr('stroke-width', 2)
    .style('cursor', 'pointer')
    .on('click', (_, d) => goToQuarter(d))
    .on('mouseenter', function(_, d) {
      const isSig = signalQtrs.has(d)
      d3.select(this).attr('r', isSig ? 8 : 5).attr('fill', '#60a5fa')
    })
    .on('mouseleave', (event, d) => {
      const isSig = signalQtrs.has(d)
      const isSel = d === currentQuarter.value
      d3.select<SVGCircleElement, string>(event.currentTarget as SVGCircleElement)
        .attr('r',    isSig ? 6 : (isSel ? 5 : 3))
        .attr('fill', isSig ? '#ef4444' : (isSel ? '#60a5fa' : '#334155'))
    })

  // Signal ⚠ labels
  quarters.value.filter(q => signalQtrs.has(q)).forEach(q => {
    g.append('text')
      .attr('x', tScale!(q) ?? 0).attr('y', 16)
      .attr('text-anchor', 'middle')
      .attr('fill', '#ef4444').attr('font-size', 11)
      .attr('pointer-events', 'none')
      .text('⚠')
  })

  // Year labels (Q1 only)
  quarters.value.filter(q => q.endsWith('Q1')).forEach(q => {
    g.append('text')
      .attr('x', tScale!(q) ?? 0).attr('y', 52)
      .attr('text-anchor', 'middle')
      .attr('fill', '#475569').attr('font-size', 10)
      .text(q.slice(0, 4))
  })

  // Playhead vertical line
  const phX = tScale!(currentQuarter.value) ?? 0
  tPlayhead = g.append('line')
    .attr('x1', phX).attr('x2', phX)
    .attr('y1', 16).attr('y2', 44)
    .attr('stroke', '#60a5fa').attr('stroke-width', 2)
    .attr('opacity', 0.9)
    .attr('pointer-events', 'none')

  refreshDotStyles()
}

function refreshDotStyles() {
  if (!tsvg) return
  const signalQtrs = new Set(signalEvents.value.map((e: any) => e.quarter))
  tsvg.selectAll<SVGCircleElement, string>('.q-dot')
    .attr('r',    d => signalQtrs.has(d) ? 6 : (d === currentQuarter.value ? 5 : 3))
    .attr('fill', d => signalQtrs.has(d) ? '#ef4444' : (d === currentQuarter.value ? '#60a5fa' : '#334155'))
    .attr('stroke', d => d === currentQuarter.value ? '#93c5fd' : 'none')
}

function movePlayheads() {
  if (!tScale) return
  const q    = currentQuarter.value
  const phX  = tScale(q) ?? 0
  tPlayhead?.attr('x1', phX).attr('x2', phX)

  const hIdx = quarters.value.indexOf(q)
  const hphX = hmLabelW + (hIdx + 0.5) * hmCellW
  hPlayhead?.attr('x1', hphX).attr('x2', hphX)

  refreshDotStyles()
}

// ── Playback ────────────────────────────────────────────────────────────────
function seek(idx: number) {
  quarterIdx.value = Math.max(0, Math.min(idx, quarters.value.length - 1))
  movePlayheads()
}

function stepForward() { seek(quarterIdx.value + 1) }
function stepBack()    { seek(quarterIdx.value - 1) }

function togglePlay() { isPlaying.value ? stopPlay() : startPlay() }

function startPlay() {
  if (!quarters.value.length) return
  if (quarterIdx.value >= quarters.value.length - 1) quarterIdx.value = 0
  isPlaying.value = true
  playTimer = setInterval(() => {
    if (quarterIdx.value < quarters.value.length - 1) {
      seek(quarterIdx.value + 1)
    } else {
      stopPlay()
    }
  }, speed.value)
}

function stopPlay() {
  isPlaying.value = false
  if (playTimer) { clearInterval(playTimer); playTimer = null }
}

function reset() { stopPlay(); seek(0) }

function onSpeedChange() {
  if (isPlaying.value) { stopPlay(); startPlay() }
}

function goToQuarter(q: string) {
  const idx = quarters.value.indexOf(q)
  if (idx >= 0) seek(idx)
}

// ── Keyboard shortcuts ──────────────────────────────────────────────────────
function onKeydown(e: KeyboardEvent) {
  const tag = (e.target as HTMLElement)?.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA') return
  if (e.code === 'Space')      { e.preventDefault(); togglePlay() }
  if (e.code === 'ArrowRight') { e.preventDefault(); stepForward() }
  if (e.code === 'ArrowLeft')  { e.preventDefault(); stepBack() }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => {
  stopPlay()
  window.removeEventListener('keydown', onKeydown)
})

// ── Helpers ──────────────────────────────────────────────────────────────────
function toPercent(f: number) { return `${Math.round(f * 100)}%` }

function barGradient(p: TrendPoint): string {
  if (p.signal_flag)                  return 'linear-gradient(90deg,#b91c1c,#ef4444)'
  if (p.normalized_frequency > 0.7)  return 'linear-gradient(90deg,#c2410c,#f97316)'
  if (p.normalized_frequency > 0.35) return 'linear-gradient(90deg,#a16207,#eab308)'
  return 'linear-gradient(90deg,#1d4ed8,#3b82f6)'
}

function confidenceType(c: string) {
  if (c === 'high')   return 'success'
  if (c === 'medium') return 'warning'
  return 'info'
}
</script>

<style scoped>
.trend-container { padding: 16px 0; font-size: 0.82rem; }

/* ── Header ── */
.trend-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 10px; flex-wrap: wrap; gap: 10px;
}
.vis-title {
  font-size: 0.95rem; font-weight: 700; color: #cbd5e1;
  display: flex; align-items: center; gap: 6px; margin: 0;
}
.controls { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.quarter-label {
  font-size: 0.85rem; font-weight: 700; color: #60a5fa;
  min-width: 72px; text-align: right; font-variant-numeric: tabular-nums;
}
.emoji { font-style: normal; }

/* ── Narrative ── */
.narrative {
  display: flex; align-items: flex-start; gap: 8px;
  background: #1e293b; border-radius: 8px; padding: 9px 13px;
  color: #94a3b8; font-size: 0.82rem; margin-bottom: 12px;
  border-left: 3px solid #334155;
}
.fade-enter-active, .fade-leave-active { transition: opacity .25s, transform .25s; }
.fade-enter-from { opacity: 0; transform: translateY(-4px); }
.fade-leave-to   { opacity: 0; }

/* ── Placeholder states ── */
.trend-placeholder { padding: 28px 0; text-align: center; }
.loading-note { color: #64748b; margin-top: 10px; font-size: 0.8rem; }

/* ── Section labels ── */
.section-label {
  font-size: 0.68rem; text-transform: uppercase; letter-spacing: .07em;
  color: #475569; margin-bottom: 6px; font-weight: 600;
}

/* ── Heatmap ── */
.heatmap-wrap { margin-bottom: 6px; overflow: hidden; }

/* ── Timeline ── */
.timeline-wrap { margin-bottom: 4px; overflow: hidden; }

/* ── Body bars ── */
.body-bars { display: flex; flex-direction: column; gap: 5px; }
.bar-list-enter-active,
.bar-list-leave-active { transition: all .25s; }
.bar-list-enter-from, .bar-list-leave-to { opacity: 0; transform: translateX(-8px); }

.bar-row {
  display: grid;
  grid-template-columns: 82px 1fr 50px auto;
  align-items: center; gap: 8px;
}
.bar-label { font-size: 0.76rem; color: #94a3b8; text-transform: capitalize; }
.bar-track {
  height: 11px; background: #1e293b; border-radius: 6px; overflow: hidden;
}
.bar-fill {
  height: 100%; border-radius: 6px;
  transition: width .28s ease, background .28s ease;
}
.bar-count { font-size: 0.7rem; color: #64748b; text-align: right; font-variant-numeric: tabular-nums; }

.conf-pill {
  font-size: 0.62rem; text-transform: uppercase; letter-spacing: .04em;
  padding: 1px 6px; border-radius: 6px; border: 1px solid currentColor;
  white-space: nowrap;
}
.conf-high   { color: #4ade80; }
.conf-medium { color: #facc15; }
.conf-low, .conf-insufficient { color: #64748b; }

.no-data-sm { color: #475569; font-size: 0.78rem; padding: 6px 0; font-style: italic; }

/* ── Signal events ── */
.signal-list { margin-top: 16px; }
.signal-title {
  font-size: 0.7rem; text-transform: uppercase; letter-spacing: .06em;
  color: #64748b; margin-bottom: 6px; font-weight: 600;
}
.signal-hint { color: #334155; font-weight: 400; }
.signal-item {
  display: flex; align-items: center; gap: 8px;
  padding: 5px 6px; border-radius: 6px; cursor: pointer;
  transition: background .12s;
}
.signal-item:hover { background: rgba(239,68,68,.07); }
.signal-body { color: #94a3b8; flex: 1; text-transform: capitalize; }
.signal-pct  { color: #f87171; font-size: 0.75rem; }

/* ── Footer note ── */
.data-note { font-size: 0.68rem; color: #334155; margin-top: 18px; }
kbd {
  background: #1e293b; border: 1px solid #334155; border-radius: 4px;
  padding: 1px 5px; font-size: 0.68rem; color: #94a3b8;
}
</style>
