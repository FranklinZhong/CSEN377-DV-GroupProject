<!--
  TrendAnimation.vue — Vis 2  FAERS static heatmap + Co-activation Matrix  v4.2
  Fixes: ① missing vs zero distinction  ② color legend  ③ row click highlight  ④ body map sync
-->
<template>
  <div class="trend-container" ref="containerRef">

    <div v-if="loading" class="trend-placeholder">
      <div class="trend-skeleton">
        <div class="skeleton-bar" v-for="i in 4" :key="i"></div>
      </div>
      <p class="loading-note">Querying FDA FAERS API — first load may take up to 30 s; results cached for 7 days.</p>
    </div>
    <div v-else-if="error" class="trend-placeholder">
      <p class="trend-error">{{ error }}</p>
    </div>
    <div v-else-if="!years.length" class="trend-placeholder">
      <p class="trend-empty">No FAERS trend data available for this drug.</p>
    </div>

    <template v-else>

      <!-- ── 1. XY Heatmap ── -->
      <div class="section-label">Adverse Event Reports — Year × Body System</div>
      <p class="section-sub">
        Color intensity = normalized report frequency (row-wise).
        Click a row to pin it. <span v-if="selectedRow" class="pin-hint">{{ selectedRow }} pinned · click again to clear</span>
      </p>


      <div class="heatmap-outer">
        <div class="heatmap-wrap" ref="heatmapRef"></div>
      </div>

      <!-- Legend bar -->
      <div class="hm-legend">
        <span class="legend-label">Low</span>
        <div class="legend-bar"></div>
        <span class="legend-label">High</span>
        <span class="legend-sep">·</span>
        <span class="legend-swatch missing-swatch"></span>
        <span class="legend-label">No data (API gap)</span>
        <span class="legend-sep">·</span>
        <span class="legend-swatch zero-swatch"></span>
        <span class="legend-label">Zero reports</span>
        <span class="legend-sep">·</span>
        <span class="legend-swatch spike-swatch"></span>
        <span class="legend-label">CUSUM spike ⚠</span>
      </div>

      <!-- ── 2. Co-activation Matrix ── -->
      <div v-if="correlationData" class="corr-section">
        <div class="section-label" style="margin-top:28px">Body System Co-activation</div>
        <p class="section-sub">
          Pearson correlation of annual report counts.
          <span class="legend-inline">
            <span class="swatch swatch-pos"></span>co-activate &nbsp;
            <span class="swatch swatch-neg"></span>counter-activate
          </span>
        </p>
        <div class="corr-outer">
          <div class="corr-wrap" ref="corrMatrixRef"></div>
        </div>
      </div>

      <!-- ── 3. Signal events ── -->
      <div v-if="yearSignalEvents.length" class="signal-list">
        <p class="signal-title">CUSUM Signal Years ({{ yearSignalEvents.length }})</p>
        <div v-for="ev in yearSignalEvents" :key="ev.year" class="signal-item">
          <span class="sig-year">{{ ev.year }}</span>
          <span class="signal-body">{{ ev.body_parts.join(' · ') }}</span>
        </div>
      </div>

      <p class="data-note">
        Source: FDA FAERS API · CUSUM ⚠ = statistically unusual quarterly spike ·
        Color normalized per body system row
      </p>
    </template>
  </div>

  <!-- Tooltip teleported to body so position:fixed always works relative to viewport -->
  <Teleport to="body">
    <div class="hm-tooltip" v-show="tooltip.show" :style="tooltipStyle">
      <template v-if="tooltip.mode === 'heatmap'">
        <div class="tt-year">{{ tooltip.year }}</div>
        <div class="tt-part">{{ tooltip.part }}</div>
        <div class="tt-count" v-if="tooltip.total > 0">{{ tooltip.total.toLocaleString() }} reports</div>
        <div class="tt-missing" v-else-if="tooltip.hasMissing">No data (API gap)</div>
        <div class="tt-zero" v-else>0 reports recorded</div>
        <div class="tt-sig" v-if="tooltip.signal">⚠ CUSUM signal detected</div>
      </template>
      <template v-else>
        <div class="tt-corr-pair">{{ tooltip.partA }}</div>
        <div class="tt-corr-sym">↔</div>
        <div class="tt-corr-pair">{{ tooltip.partB }}</div>
        <div class="tt-corr-r" :class="tooltip.r >= 0 ? 'r-pos' : 'r-neg'">r = {{ formatR(tooltip.r) }}</div>
        <div class="tt-corr-hint">{{ corrHint(tooltip.r) }}</div>
      </template>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted, nextTick } from 'vue'
import * as d3 from 'd3'
import { api } from '../api/client'
import type { TrendPoint } from '../api/client'

const props = defineProps<{
  drugId: number
  hoveredPart?: string | null
}>()

// ── State ──────────────────────────────────────────────────────────────────
const loading      = ref(false)
const error        = ref('')
const timeline     = ref<TrendPoint[]>([])
const signalEvents = ref<any[]>([])
const selectedRow  = ref<string | null>(null)

const heatmapRef    = ref<HTMLElement | null>(null)
const corrMatrixRef = ref<HTMLElement | null>(null)

let hsvg: d3.Selection<SVGSVGElement, unknown, null, undefined> | null = null
let csvg: d3.Selection<SVGSVGElement, unknown, null, undefined> | null = null
let rowOverlayGroup: d3.Selection<SVGGElement, unknown, null, undefined> | null = null

// ── Tooltip ────────────────────────────────────────────────────────────────
const tooltip = ref({
  show: false, x: 0, y: 0,
  mode: 'heatmap' as 'heatmap' | 'corr',
  year: '', part: '', total: 0, signal: false, hasMissing: false,
  partA: '', partB: '', r: 0,
})

const tooltipStyle = computed(() => ({
  position: 'fixed' as const,
  left:  `${tooltip.value.x + 14}px`,
  top:   `${tooltip.value.y + 4}px`,
  pointerEvents: 'none' as const,
  zIndex: 999,
}))

// ── Yearly aggregation ─────────────────────────────────────────────────────
type YearEntry = { total: number; signal: boolean; hasMissing: boolean }

const yearData = computed(() => {
  const map: Record<string, Record<string, YearEntry>> = {}
  for (const p of timeline.value) {
    const year = p.quarter.slice(0, 4)
    if (!map[year]) map[year] = {}
    const entry = map[year][p.body_part]
    if (entry) {
      entry.total      += p.report_count
      entry.signal      = entry.signal || p.signal_flag
      entry.hasMissing  = entry.hasMissing || p.missing
    } else {
      map[year][p.body_part] = { total: p.report_count, signal: p.signal_flag, hasMissing: p.missing }
    }
  }
  return map
})

const years = computed(() => Object.keys(yearData.value).sort())

const allBodyParts = computed(() => {
  const totals: Record<string, number> = {}
  for (const parts of Object.values(yearData.value))
    for (const [bp, d] of Object.entries(parts))
      totals[bp] = (totals[bp] ?? 0) + d.total
  return Object.entries(totals)
    .sort((a, b) => b[1] - a[1])
    .map(([k]) => k)
})

const yearSignalEvents = computed(() => {
  const byYear: Record<string, Set<string>> = {}
  for (const ev of signalEvents.value) {
    const year = String(ev.quarter ?? '').slice(0, 4)
    if (!year) continue
    if (!byYear[year]) byYear[year] = new Set()
    byYear[year].add(ev.body_part)
  }
  return Object.entries(byYear)
    .map(([year, parts]) => ({ year, body_parts: [...parts] }))
    .sort((a, b) => a.year.localeCompare(b.year))
})

const signalYearSet = computed(() => new Set(yearSignalEvents.value.map(e => e.year)))

// ── Row highlight ──────────────────────────────────────────────────────────
function getActiveRow(): string | null {
  return selectedRow.value ?? props.hoveredPart ?? null
}

function highlightRow(part: string | null) {
  if (!rowOverlayGroup) return
  const parts  = allBodyParts.value
  const isSelected = !!selectedRow.value
  rowOverlayGroup.selectAll<SVGRectElement, unknown>('.row-hl')
    .attr('opacity', (_: unknown, i: number) => {
      if (!part) return 0
      return parts[i]?.toLowerCase() === part.toLowerCase() ? 1 : 0
    })
    .attr('fill',   isSelected ? 'rgba(201,168,76,0.15)' : 'rgba(201,168,76,0.09)')
    .attr('stroke', isSelected ? '#c9a84c' : 'rgba(201,168,76,0.45)')
}

watch([() => props.hoveredPart, selectedRow], () => {
  highlightRow(getActiveRow())
})

// ── Correlation ────────────────────────────────────────────────────────────
function pearson(a: number[], b: number[]): number {
  const n = a.length
  if (n < 3) return 0
  const ma = a.reduce((s, x) => s + x, 0) / n
  const mb = b.reduce((s, x) => s + x, 0) / n
  let num = 0, da = 0, db = 0
  for (let i = 0; i < n; i++) {
    const ea = a[i] - ma, eb = b[i] - mb
    num += ea * eb; da += ea * ea; db += eb * eb
  }
  if (da === 0 || db === 0) return 0
  return Math.max(-1, Math.min(1, num / Math.sqrt(da * db)))
}

const correlationData = computed(() => {
  const parts = allBodyParts.value
  const ys    = years.value
  if (parts.length < 2 || ys.length < 3) return null
  const series: Record<string, number[]> = {}
  for (const part of parts)
    series[part] = ys.map(y => yearData.value[y]?.[part]?.total ?? 0)
  const matrix: { partA: string; partB: string; r: number }[] = []
  for (const a of parts)
    for (const b of parts)
      matrix.push({ partA: a, partB: b, r: pearson(series[a], series[b]) })
  return { parts, matrix }
})

function formatR(r: number) { return (r >= 0 ? '+' : '') + r.toFixed(2) }
function corrHint(r: number) {
  const abs = Math.abs(r)
  if (abs < 0.2) return 'Weak / no relationship'
  if (abs < 0.5) return r > 0 ? 'Moderate co-activation'    : 'Moderate counter-activation'
  if (abs < 0.8) return r > 0 ? 'Strong co-activation'      : 'Strong counter-activation'
  return                r > 0 ? 'Very strong co-activation' : 'Very strong counter-activation'
}

// ── Data loading ────────────────────────────────────────────────────────────
async function load(id: number) {
  loading.value      = true
  error.value        = ''
  timeline.value     = []
  signalEvents.value = []
  selectedRow.value  = null
  hsvg = csvg = rowOverlayGroup = null

  try {
    const res = await api.getTrend(id)
    if (res.data.success) {
      timeline.value     = res.data.data.timeline      ?? []
      signalEvents.value = res.data.data.signal_events ?? []
    } else {
      error.value = 'Trend data unavailable for this drug.'
    }
  } catch {
    error.value = 'Failed to fetch trend data from FDA FAERS.'
  } finally {
    loading.value = false
  }

  if (!error.value && years.value.length) {
    await nextTick()
    buildHeatmap()
    buildCorrelationMatrix()
  }
}

watch(() => props.drugId, load, { immediate: true })

// ── D3: XY Heatmap ──────────────────────────────────────────────────────────
function buildHeatmap() {
  const el = heatmapRef.value
  if (!el || !years.value.length) return
  el.innerHTML = ''
  hsvg = rowOverlayGroup = null

  const ys    = years.value
  const parts = allBodyParts.value
  if (!parts.length) return

  const CELL_W = 52, CELL_H = 64
  const ML = 142, MT = 10, MR = 16, MB = 28

  const W = ML + ys.length * CELL_W + MR
  const H = MT + parts.length * CELL_H + MB

  const rowMax: Record<string, number> = {}
  for (const part of parts) {
    rowMax[part] = d3.max(ys, (y: string) => yearData.value[y]?.[part]?.total ?? 0) ?? 1
    if (rowMax[part] === 0) rowMax[part] = 1
  }

  const colorScale = d3.scaleSequential(d3.interpolateYlOrRd).domain([0, 1])

  hsvg = d3.select(el).append('svg').attr('width', W).attr('height', H)

  // ── SVG defs: missing-data stripe pattern ──
  const defs = hsvg.append('defs')
  const pat  = defs.append('pattern')
    .attr('id', 'missing-pat').attr('width', 5).attr('height', 5)
    .attr('patternUnits', 'userSpaceOnUse').attr('patternTransform', 'rotate(45)')
  pat.append('rect').attr('width', 5).attr('height', 5).attr('fill', '#0c1629')
  pat.append('line').attr('x1', 0).attr('y1', 0).attr('x2', 0).attr('y2', 5)
    .attr('stroke', '#1d2d48').attr('stroke-width', 2)

  const g = hsvg.append('g').attr('transform', `translate(${ML},${MT})`)

  // ── Cells ──
  parts.forEach((part, ri) => {
    ys.forEach((year, ci) => {
      const d          = yearData.value[year]?.[part]
      const raw        = d?.total      ?? 0
      const sig        = d?.signal     ?? false
      const hasMissing = d?.hasMissing ?? false
      const norm       = raw / rowMax[part]

      let fill: string
      if (raw > 0)      fill = colorScale(norm)
      else if (hasMissing) fill = 'url(#missing-pat)'
      else              fill = '#09111e'

      g.append('rect')
        .attr('x',      ci * CELL_W + 1).attr('y', ri * CELL_H + 1)
        .attr('width',  CELL_W - 2).attr('height', CELL_H - 2)
        .attr('rx', 3)
        .attr('fill',         fill)
        .attr('stroke',       sig ? '#ef4444' : 'rgba(255,255,255,0.04)')
        .attr('stroke-width', sig ? 2 : 0.5)
        .style('cursor', 'pointer')
        .on('mouseenter', (event: MouseEvent) => {
          tooltip.value = { ...tooltip.value, show: true, mode: 'heatmap',
            x: event.clientX, y: event.clientY, year, part, total: raw, signal: sig, hasMissing }
          d3.select<SVGRectElement, unknown>(event.currentTarget as SVGRectElement).attr('opacity', 0.72)
        })
        .on('mousemove', (event: MouseEvent) => {
          tooltip.value.x = event.clientX; tooltip.value.y = event.clientY
        })
        .on('mouseleave', (event: MouseEvent) => {
          tooltip.value.show = false
          d3.select<SVGRectElement, unknown>(event.currentTarget as SVGRectElement).attr('opacity', 1)
        })
        .on('click', () => {
          selectedRow.value = selectedRow.value === part ? null : part
        })

      if (sig) {
        const cx = ci * CELL_W + CELL_W / 2
        const cy = ri * CELL_H + CELL_H / 2
        const badge = g.append('g')
          .attr('transform', `translate(${cx},${cy})`)
          .attr('pointer-events', 'none')
        badge.append('circle')
          .attr('r', 9)
          .attr('fill', 'rgba(0,0,0,0.45)')
          .attr('stroke', '#ef4444')
          .attr('stroke-width', 1)
        badge.append('text')
          .attr('text-anchor', 'middle')
          .attr('dominant-baseline', 'central')
          .attr('fill', '#ffffff')
          .attr('font-size', '12px')
          .attr('font-family', 'system-ui, sans-serif')
          .attr('pointer-events', 'none')
          .text('⚠')
      }
    })
  })

  // ── Y-axis labels ──
  parts.forEach((part, ri) => {
    hsvg!.append('text')
      .attr('x', ML - 10).attr('y', MT + ri * CELL_H + CELL_H / 2)
      .attr('text-anchor', 'end').attr('dominant-baseline', 'middle')
      .attr('fill', '#9c9590').attr('font-size', 12)
      .text(part.length > 19 ? part.slice(0, 18) + '…' : part)
  })

  // ── X-axis labels + signal triangles ──
  ys.forEach((year, ci) => {
    const isSig = signalYearSet.value.has(year)
    const cx    = ci * CELL_W + CELL_W / 2
    if (isSig) {
      g.append('polygon')
        .attr('points', `${cx},${parts.length * CELL_H + 3} ${cx - 4},${parts.length * CELL_H + 11} ${cx + 4},${parts.length * CELL_H + 11}`)
        .attr('fill', '#ef4444').attr('opacity', 0.85).style('pointer-events', 'none')
    }
    g.append('text')
      .attr('x', cx).attr('y', parts.length * CELL_H + (isSig ? 24 : 18))
      .attr('text-anchor', 'middle')
      .attr('fill', isSig ? '#f87171' : '#6b6560')
      .attr('font-size', 11).attr('font-weight', isSig ? '600' : '400')
      .style('pointer-events', 'none').text(year)
  })

  // ── Row highlight overlays (rendered last → on top of cells) ──
  rowOverlayGroup = hsvg.append('g').attr('class', 'row-overlay-g')
  parts.forEach((_, ri) => {
    rowOverlayGroup!.append('rect')
      .attr('class', `row-hl`)
      .attr('x', ML).attr('y', MT + ri * CELL_H)
      .attr('width', ys.length * CELL_W).attr('height', CELL_H)
      .attr('fill', 'rgba(201,168,76,0.09)')
      .attr('stroke', 'rgba(201,168,76,0.45)').attr('stroke-width', 1.5)
      .attr('rx', 2).attr('opacity', 0)
      .attr('pointer-events', 'none')
  })

  // Apply initial highlight if body map already has a hovered part
  if (getActiveRow()) highlightRow(getActiveRow())
}

// ── D3: Correlation Matrix ──────────────────────────────────────────────────
function buildCorrelationMatrix() {
  const el = corrMatrixRef.value
  if (!el) return
  el.innerHTML = ''
  csvg = null

  const cd = correlationData.value
  if (!cd) return

  const { parts, matrix } = cd
  const n = parts.length

  const CORR_CELL = 60
  const ML = 142, MT = 88, MR = 10, MB = 20

  const W = ML + n * CORR_CELL + MR
  const H = MT + n * CORR_CELL + MB

  const colorScale = d3.scaleDiverging(
    (t: number) => d3.interpolateRdBu(1 - t)
  ).domain([-1, 0, 1])

  csvg = d3.select(el).append('svg').attr('width', W).attr('height', H)
  const g = csvg.append('g').attr('transform', `translate(${ML},${MT})`)

  parts.forEach((partA, ri) => {
    parts.forEach((partB, ci) => {
      const r      = matrix.find(m => m.partA === partA && m.partB === partB)!.r
      const isDiag = ri === ci

      g.append('rect')
        .attr('x', ci * CORR_CELL + 1).attr('y', ri * CORR_CELL + 1)
        .attr('width', CORR_CELL - 2).attr('height', CORR_CELL - 2)
        .attr('rx', 3)
        .attr('fill',   isDiag ? '#141c2e' : colorScale(r))
        .attr('stroke', isDiag ? 'rgba(201,168,76,0.25)' : 'rgba(255,255,255,0.04)')
        .attr('stroke-width', 0.5)
        .style('cursor', isDiag ? 'default' : 'pointer')
        .on('mouseenter', (event: MouseEvent) => {
          if (isDiag) return
          tooltip.value = { ...tooltip.value, show: true, mode: 'corr',
            x: event.clientX, y: event.clientY, partA, partB, r }
          d3.select<SVGRectElement, unknown>(event.currentTarget as SVGRectElement).attr('opacity', 0.72)
        })
        .on('mousemove', (event: MouseEvent) => {
          tooltip.value.x = event.clientX; tooltip.value.y = event.clientY
        })
        .on('mouseleave', (event: MouseEvent) => {
          tooltip.value.show = false
          d3.select<SVGRectElement, unknown>(event.currentTarget as SVGRectElement).attr('opacity', 1)
        })

      if (!isDiag && Math.abs(r) >= 0.25) {
        g.append('text')
          .attr('x', ci * CORR_CELL + CORR_CELL / 2)
          .attr('y', ri * CORR_CELL + CORR_CELL / 2 + 1)
          .attr('text-anchor', 'middle').attr('dominant-baseline', 'middle')
          .attr('fill', Math.abs(r) > 0.65 ? 'rgba(255,255,255,0.88)' : 'rgba(0,0,0,0.65)')
          .attr('font-size', 10).attr('font-weight', '600')
          .attr('pointer-events', 'none').text(r.toFixed(2))
      }
      if (isDiag) {
        g.append('text')
          .attr('x', ci * CORR_CELL + CORR_CELL / 2)
          .attr('y', ri * CORR_CELL + CORR_CELL / 2 + 1)
          .attr('text-anchor', 'middle').attr('dominant-baseline', 'middle')
          .attr('fill', 'rgba(201,168,76,0.5)').attr('font-size', 12)
          .attr('pointer-events', 'none').text('—')
      }
    })
  })

  parts.forEach((part, ri) => {
    csvg!.append('text')
      .attr('x', ML - 10).attr('y', MT + ri * CORR_CELL + CORR_CELL / 2)
      .attr('text-anchor', 'end').attr('dominant-baseline', 'middle')
      .attr('fill', '#9c9590').attr('font-size', 12)
      .text(part.length > 19 ? part.slice(0, 18) + '…' : part)
  })

  parts.forEach((part, ci) => {
    csvg!.append('text')
      .attr('transform', `translate(${ML + ci * CORR_CELL + CORR_CELL / 2},${MT - 10}) rotate(-45)`)
      .attr('text-anchor', 'start').attr('fill', '#9c9590').attr('font-size', 11)
      .text(part.length > 15 ? part.slice(0, 14) + '…' : part)
  })

  const lgW = 96, lgH = 8, lgX = W - MR - lgW, lgY = H - MB + 4
  const lgDef = csvg.append('defs').append('linearGradient')
    .attr('id', 'corr-grad').attr('x1', '0').attr('x2', '1')
  lgDef.append('stop').attr('offset', '0%').attr('stop-color',   colorScale(-1))
  lgDef.append('stop').attr('offset', '50%').attr('stop-color',  colorScale(0))
  lgDef.append('stop').attr('offset', '100%').attr('stop-color', colorScale(1))
  csvg.append('rect').attr('x', lgX).attr('y', lgY).attr('width', lgW).attr('height', lgH)
    .attr('rx', 2).attr('fill', 'url(#corr-grad)')
  for (const [label, anchor, offset] of [
    ['−1', 'start', 0], ['0', 'middle', lgW / 2], ['+1', 'end', lgW]
  ] as [string, string, number][]) {
    csvg.append('text').attr('x', lgX + offset).attr('y', lgY - 3)
      .attr('text-anchor', anchor).attr('fill', '#6b6560').attr('font-size', 10).text(label)
  }
}

onUnmounted(() => { tooltip.value.show = false })
</script>

<style scoped>
.trend-container { padding: 16px 0; font-size: 0.82rem; color: var(--text); position: relative; }

.section-label {
  font-family: var(--font-mono); font-size: 0.72rem; text-transform: uppercase;
  letter-spacing: .08em; color: var(--gold); margin-bottom: 6px; font-weight: 600;
}
.section-sub {
  font-size: 0.78rem; color: var(--text2); margin-bottom: 10px;
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap; line-height: 1.5;
}
.pin-hint { color: var(--gold); font-size: 0.72rem; font-family: var(--font-mono); }

.legend-inline { display: inline-flex; align-items: center; gap: 5px; color: var(--muted); }
.swatch { display: inline-block; width: 12px; height: 12px; border-radius: 2px; vertical-align: middle; }
.swatch-pos { background: #ef4444; }
.swatch-neg { background: #3b82f6; }

/* ── Placeholder ── */
.trend-placeholder { padding: 28px 0; text-align: center; }
.loading-note { color: var(--muted); margin-top: 10px; font-size: 0.8rem; font-style: italic; }
.trend-error  { color: var(--side); font-size: 0.85rem; }
.trend-empty  { color: var(--muted); font-size: 0.85rem; font-style: italic; }
.trend-skeleton { display: flex; flex-direction: column; gap: 8px; }
.skeleton-bar {
  height: 22px;
  background: linear-gradient(90deg, var(--bg3) 25%, var(--bg2) 50%, var(--bg3) 75%);
  background-size: 200% 100%; animation: sk-shimmer 1.4s infinite; border-radius: var(--radius);
}
@keyframes sk-shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

/* ── Heatmap ── */
.heatmap-outer {
  overflow-x: auto;
  padding-bottom: 2px;
  display: flex;
  justify-content: safe center;
}
.heatmap-wrap { flex-shrink: 0; }

/* ── Legend bar ── */
.hm-legend {
  display: flex; align-items: center; gap: 7px; margin-top: 10px;
  font-size: 0.72rem; color: var(--muted); flex-wrap: wrap;
}
.legend-label { white-space: nowrap; }
.legend-bar   { width: 72px; height: 10px; border-radius: 2px; background: linear-gradient(90deg, #ffffcc, #feb24c, #f03b20, #bd0026); flex-shrink: 0; }
.legend-swatch { display: inline-block; width: 16px; height: 10px; border-radius: 2px; flex-shrink: 0; }
.missing-swatch { background: repeating-linear-gradient(-45deg, #0c1629 0px, #0c1629 2px, #1d2d48 2px, #1d2d48 4px); }
.zero-swatch    { background: #09111e; border: 1px solid #1a2540; }
.spike-swatch   { background: transparent; border: 2px solid #ef4444; }
.legend-sep     { color: var(--border2); }

/* ── Tooltip ── */
.hm-tooltip {
  background: rgba(6, 10, 22, 0.96); border: 1px solid rgba(201,168,76,0.4);
  border-radius: 6px; padding: 8px 12px; min-width: 160px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.5);
}
.tt-year    { font-family: var(--font-mono); font-size: 0.7rem; color: var(--gold); font-weight: 700; margin-bottom: 3px; }
.tt-part    { font-size: 0.82rem; color: var(--text); font-weight: 500; margin-bottom: 2px; }
.tt-count   { font-family: var(--font-mono); font-size: 0.76rem; color: var(--text2); }
.tt-missing { font-size: 0.72rem; color: #60a5fa; }
.tt-zero    { font-size: 0.72rem; color: var(--muted); }
.tt-sig     { font-size: 0.72rem; color: #f87171; margin-top: 4px; }
.tt-corr-pair { font-size: 0.8rem; color: var(--text); font-weight: 500; }
.tt-corr-sym  { font-size: 0.75rem; color: var(--muted); margin: 2px 0; }
.tt-corr-r    { font-family: var(--font-mono); font-size: 0.82rem; font-weight: 700; margin: 4px 0 2px; }
.r-pos        { color: #f87171; }
.r-neg        { color: #60a5fa; }
.tt-corr-hint { font-size: 0.72rem; color: var(--muted); }

/* ── Co-activation ── */
.corr-section { }
.corr-outer {
  overflow-x: auto;
  display: flex;
  justify-content: safe center;
}
.corr-wrap { flex-shrink: 0; }

/* ── Signal list ── */
.signal-list { margin-top: 20px; }
.signal-title {
  font-family: var(--font-mono); font-size: 0.72rem; text-transform: uppercase;
  letter-spacing: .06em; color: var(--muted); margin-bottom: 6px; font-weight: 600;
}
.sig-year {
  font-family: var(--font-mono); font-size: 0.72rem; padding: 1px 6px; border-radius: 2px;
  white-space: nowrap; flex-shrink: 0;
  background: rgba(239,68,68,0.12); color: #f87171; border: 1px solid rgba(239,68,68,0.25);
}
.signal-item { display: flex; align-items: center; gap: 8px; padding: 5px 6px; border-radius: var(--radius); }
.signal-body { color: var(--text2); flex: 1; text-transform: capitalize; }

.data-note {
  font-family: var(--font-mono); font-size: 0.72rem; color: var(--muted);
  margin-top: 18px; opacity: 0.7; line-height: 1.6;
}
</style>
