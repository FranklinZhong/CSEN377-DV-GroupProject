<!--
  TrendAnimation.vue — Vis 2 FAERS 季度时间轴动画

  功能：
  - 从 /api/drugs/{id}/trend 获取多年季度数据（FAERS API 实时查询）
  - D3 时间轴：2014Q1 → 现在，人体部位亮度随 report_count 变化
  - 播放 / 暂停 / 拖拽 scrubbing
  - CUSUM 信号季度标注 ⚠，hover 显示增幅
  - Narrative 文字随时间轴自动更新
-->
<template>
  <div class="trend-container">
    <!-- 标题 + 控制 -->
    <div class="trend-header">
      <h3 class="vis-title">Side Effect Trend Over Time</h3>
      <div class="controls">
        <el-button :icon="isPlaying ? 'VideoPause' : 'VideoPlay'"
                   circle size="small" @click="togglePlay" />
        <el-button icon="Refresh" circle size="small"
                   @click="reset" title="Reset to start" />
        <span class="quarter-label">{{ currentQuarter }}</span>
      </div>
    </div>

    <!-- Narrative 文字 -->
    <div class="narrative" v-if="narrativeText">
      <el-icon><InfoFilled /></el-icon> {{ narrativeText }}
    </div>

    <!-- 加载 / 空状态 -->
    <div v-if="loading" class="trend-placeholder">
      <el-skeleton :rows="2" animated />
      <p style="color:#64748b;margin-top:8px;font-size:0.85rem">
        Querying FDA FAERS API for multi-year data…
      </p>
    </div>
    <div v-else-if="error" class="trend-placeholder">
      <el-alert :title="error" type="warning" :closable="false" show-icon />
    </div>
    <div v-else-if="!quarters.length" class="trend-placeholder">
      <p style="color:#64748b">No trend data available for this drug.</p>
    </div>

    <template v-else>
      <!-- 时间轴 SVG -->
      <div class="timeline-wrap" ref="timelineRef"></div>

      <!-- 身体系统亮度条 -->
      <div class="body-bars">
        <div v-for="row in currentFrame" :key="row.body_part" class="bar-row">
          <span class="bar-label">{{ row.body_part }}</span>
          <div class="bar-track">
            <div class="bar-fill"
                 :style="{ width: (row.normalized_frequency * 100) + '%',
                           backgroundColor: barColor(row) }"
            />
          </div>
          <span class="bar-count">{{ row.report_count }}</span>
          <el-tag v-if="row.signal_flag" size="small" type="danger">⚠ signal</el-tag>
        </div>
      </div>

      <!-- 信号事件列表 -->
      <div v-if="signalEvents.length" class="signal-list">
        <p class="signal-title">Detected Signal Events</p>
        <div v-for="ev in signalEvents" :key="`${ev.quarter}-${ev.body_part}`"
             class="signal-item">
          <el-tag type="danger" size="small">{{ ev.quarter }}</el-tag>
          {{ ev.body_part }}
          <span v-if="ev.increase_pct" class="signal-pct">
            +{{ ev.increase_pct }}% vs prev quarter
          </span>
        </div>
      </div>

      <p class="data-note">
        Source: FDA FAERS API · Confidence indicators based on report volume
      </p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted, nextTick } from 'vue'
import { InfoFilled } from '@element-plus/icons-vue'
import * as d3 from 'd3'
import { api } from '../api/client'
import type { TrendPoint } from '../api/client'

const props = defineProps<{ drugId: number }>()

// ── State ──────────────────────────────────────────────────────────────
const loading     = ref(false)
const error       = ref('')
const timeline    = ref<TrendPoint[]>([])
const signalEvents = ref<any[]>([])
const quarterIdx  = ref(0)
const isPlaying   = ref(false)
const timelineRef = ref<HTMLElement | null>(null)

let timer: ReturnType<typeof setInterval> | null = null
let svg: d3.Selection<SVGSVGElement, unknown, null, undefined> | null = null

// ── Derived ────────────────────────────────────────────────────────────
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
  const top = frame[0]
  const signals = frame.filter(p => p.signal_flag)
  if (signals.length) {
    return `In ${currentQuarter.value}, ${signals[0].body_part} reports showed a significant spike.`
  }
  return `In ${currentQuarter.value}, top affected system: ${top.body_part} (${top.report_count} reports).`
})

// ── Data loading ────────────────────────────────────────────────────────
async function load(id: number) {
  loading.value = true
  error.value = ''
  timeline.value = []
  signalEvents.value = []
  quarterIdx.value = 0
  stopPlay()
  try {
    const res = await api.getTrend(id)
    if (res.data.success) {
      timeline.value   = res.data.data.timeline   ?? []
      signalEvents.value = res.data.data.signal_events ?? []
      await nextTick()
      buildTimeline()
    } else {
      error.value = 'Trend data unavailable.'
    }
  } catch {
    error.value = 'Failed to fetch trend data.'
  } finally {
    loading.value = false
  }
}

watch(() => props.drugId, load, { immediate: true })

// ── D3 timeline ─────────────────────────────────────────────────────────
function buildTimeline() {
  const el = timelineRef.value
  if (!el || !quarters.value.length) return
  el.innerHTML = ''

  const W = el.clientWidth || 600
  const H = 54
  const margin = { left: 20, right: 20 }
  const innerW = W - margin.left - margin.right

  svg = d3.select(el).append('svg')
    .attr('width', W).attr('height', H)

  const g = svg.append('g').attr('transform', `translate(${margin.left},0)`)

  const x = d3.scalePoint()
    .domain(quarters.value)
    .range([0, innerW])
    .padding(0.1)

  // Track
  g.append('line')
    .attr('x1', 0).attr('x2', innerW)
    .attr('y1', 32).attr('y2', 32)
    .attr('stroke', '#334155').attr('stroke-width', 2)

  // Signal markers
  const signalQtrs = new Set(signalEvents.value.map((e: any) => e.quarter))
  quarters.value.forEach((q, i) => {
    const cx = x(q) ?? 0
    const isSignal = signalQtrs.has(q)
    const isCurrent = i === quarterIdx.value

    g.append('circle')
      .attr('cx', cx).attr('cy', 32)
      .attr('r', isSignal ? 7 : 4)
      .attr('fill', isSignal ? '#ef4444' : '#334155')
      .attr('stroke', isCurrent ? '#60a5fa' : 'none')
      .attr('stroke-width', 2)
      .attr('class', 'q-dot')
      .attr('data-idx', i)
      .style('cursor', 'pointer')
      .on('click', () => { quarterIdx.value = i; updateDots() })

    if (isSignal) {
      g.append('text')
        .attr('x', cx).attr('y', 18)
        .attr('text-anchor', 'middle')
        .attr('fill', '#ef4444')
        .attr('font-size', 12)
        .text('⚠')
    }
  })

  // Year labels (show only Jan)
  const yearMarkers = quarters.value.filter(q => q.endsWith('Q1'))
  yearMarkers.forEach(q => {
    g.append('text')
      .attr('x', x(q) ?? 0).attr('y', 50)
      .attr('text-anchor', 'middle')
      .attr('fill', '#64748b').attr('font-size', 10)
      .text(q.slice(0, 4))
  })
}

function updateDots() {
  if (!svg) return
  svg.selectAll('.q-dot')
    .attr('stroke', function(_, i) { return i === quarterIdx.value ? '#60a5fa' : 'none' })
}

// ── Playback ────────────────────────────────────────────────────────────
function togglePlay() {
  isPlaying.value ? stopPlay() : startPlay()
}

function startPlay() {
  if (!quarters.value.length) return
  isPlaying.value = true
  timer = setInterval(() => {
    if (quarterIdx.value < quarters.value.length - 1) {
      quarterIdx.value++
      updateDots()
    } else {
      stopPlay()
    }
  }, 300)
}

function stopPlay() {
  isPlaying.value = false
  if (timer) { clearInterval(timer); timer = null }
}

function reset() {
  stopPlay()
  quarterIdx.value = 0
  updateDots()
}

onUnmounted(stopPlay)

// ── Helpers ──────────────────────────────────────────────────────────────
function barColor(p: TrendPoint) {
  if (p.signal_flag)             return '#ef4444'
  if (p.normalized_frequency > 0.6) return '#f97316'
  if (p.normalized_frequency > 0.3) return '#eab308'
  return '#3b82f6'
}
</script>

<style scoped>
.trend-container { padding: 16px 0; }
.trend-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 12px;
}
.vis-title { font-size: 0.95rem; font-weight: 600; color: #cbd5e1; }
.controls { display: flex; align-items: center; gap: 8px; }
.quarter-label {
  font-size: 0.85rem; font-weight: 700; color: #60a5fa;
  min-width: 72px; text-align: right;
}
.narrative {
  display: flex; align-items: center; gap: 6px;
  background: #1e293b; border-radius: 8px; padding: 8px 12px;
  color: #94a3b8; font-size: 0.82rem; margin-bottom: 12px;
}
.trend-placeholder {
  padding: 24px 0; text-align: center;
}
.timeline-wrap { margin-bottom: 16px; }
.body-bars { display: flex; flex-direction: column; gap: 6px; }
.bar-row {
  display: grid;
  grid-template-columns: 90px 1fr 48px auto;
  align-items: center; gap: 8px;
}
.bar-label { font-size: 0.78rem; color: #94a3b8; text-transform: capitalize; }
.bar-track {
  height: 10px; background: #1e293b; border-radius: 5px; overflow: hidden;
}
.bar-fill {
  height: 100%; border-radius: 5px;
  transition: width 0.25s ease, background-color 0.25s ease;
}
.bar-count { font-size: 0.72rem; color: #64748b; text-align: right; }
.signal-list { margin-top: 16px; }
.signal-title { font-size: 0.75rem; color: #64748b; text-transform: uppercase; margin-bottom: 6px; }
.signal-item {
  display: flex; align-items: center; gap: 8px;
  font-size: 0.82rem; color: #94a3b8; padding: 4px 0;
  border-bottom: 1px solid #1e293b;
}
.signal-pct { color: #f87171; }
.data-note { font-size: 0.7rem; color: #475569; margin-top: 16px; }
</style>
