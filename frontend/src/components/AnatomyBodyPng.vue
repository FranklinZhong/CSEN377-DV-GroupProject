<!--
  AnatomyBodyPng.vue — prototype: PNG base image + ellipse glow overlay
  Preview only; does not replace AnatomyBody.vue
-->
<template>
  <div class="anatomy-wrap" :class="{ 'reduce-motion': reduceMotion }">

    <!-- View Mode Toggle (same interface) -->
    <div class="mode-toggle" v-if="showToggle">
      <button
        v-for="opt in modeOpts" :key="opt.value"
        class="mode-btn"
        :class="[`mode-${opt.value}`, { 'mode-active': viewMode === opt.value, 'mode-disabled': opt.disabled }]"
        :disabled="opt.disabled"
        @click="$emit('update:viewMode', opt.value)"
      >
        <span class="mode-dot" :style="{ background: opt.color }"></span>
        {{ opt.label }}
        <span v-if="opt.count" class="mode-count">{{ opt.count }}</span>
      </button>
    </div>

    <svg viewBox="0 0 420 840" xmlns="http://www.w3.org/2000/svg" class="anatomy-svg">

      <!-- ── Base: anatomy PNG ── -->
      <image href="/anatomy-hero.png" x="0" y="0" width="420" height="840"
             preserveAspectRatio="xMidYMid meet"/>

      <!-- ── Organ overlay ellipses ── -->
      <g class="organs">

        <!-- BRAIN -->
        <g v-bind="organHandlers('brain')" class="organ-group" :class="organClass('brain')">
          <ellipse cx="210" cy="82"  rx="44" ry="36"/>
        </g>

        <!-- EYE -->
        <g v-bind="organHandlers('eye')" class="organ-group" :class="organClass('eye')">
          <ellipse cx="178" cy="113" rx="14" ry="8"/>
          <ellipse cx="242" cy="113" rx="14" ry="8"/>
        </g>

        <!-- EAR -->
        <g v-bind="organHandlers('ear')" class="organ-group" :class="organClass('ear')">
          <ellipse cx="146" cy="122" rx="11" ry="15"/>
          <ellipse cx="274" cy="122" rx="11" ry="15"/>
        </g>

        <!-- HEART -->
        <g v-bind="organHandlers('heart')" class="organ-group" :class="organClass('heart')">
          <ellipse cx="193" cy="272" rx="32" ry="34"/>
        </g>

        <!-- LUNG -->
        <g v-bind="organHandlers('lung')" class="organ-group" :class="organClass('lung')">
          <ellipse cx="158" cy="268" rx="30" ry="50"/>
          <ellipse cx="262" cy="268" rx="30" ry="50"/>
        </g>

        <!-- LIVER -->
        <g v-bind="organHandlers('liver')" class="organ-group" :class="organClass('liver')">
          <ellipse cx="238" cy="362" rx="48" ry="28"/>
        </g>

        <!-- STOMACH -->
        <g v-bind="organHandlers('stomach')" class="organ-group" :class="organClass('stomach')">
          <ellipse cx="184" cy="376" rx="30" ry="27"/>
        </g>

        <!-- KIDNEY -->
        <g v-bind="organHandlers('kidney')" class="organ-group" :class="organClass('kidney')">
          <ellipse cx="173" cy="424" rx="16" ry="24"/>
          <ellipse cx="247" cy="424" rx="16" ry="24"/>
        </g>

        <!-- SKIN: invisible large hit area over body silhouette -->
        <g v-bind="organHandlers('skin')" class="organ-group skin-group" :class="organClass('skin')">
          <ellipse cx="210" cy="480" rx="78" ry="210"/>
        </g>

        <!-- MUSCLE: thighs -->
        <g v-bind="organHandlers('muscle')" class="organ-group" :class="organClass('muscle')">
          <ellipse cx="168" cy="615" rx="27" ry="55"/>
          <ellipse cx="252" cy="615" rx="27" ry="55"/>
        </g>

        <!-- BLOOD: arm vessels -->
        <g v-bind="organHandlers('blood')" class="organ-group" :class="organClass('blood')">
          <ellipse cx="100" cy="390" rx="9" ry="50"/>
          <ellipse cx="320" cy="390" rx="9" ry="50"/>
        </g>

        <!-- VASCULAR: aortic arch region -->
        <g v-bind="organHandlers('vascular')" class="organ-group" :class="organClass('vascular')">
          <ellipse cx="210" cy="244" rx="22" ry="16"/>
        </g>

        <!-- ENDOCRINE: thyroid (neck) + pituitary (brain base) + adrenals -->
        <g v-bind="organHandlers('endocrine')" class="organ-group" :class="organClass('endocrine')">
          <ellipse cx="210" cy="155" rx="25" ry="13"/>
          <ellipse cx="173" cy="398" rx="12" ry="8"/>
          <ellipse cx="247" cy="398" rx="12" ry="8"/>
        </g>

        <!-- REPRODUCTIVE: lower pelvis -->
        <g v-bind="organHandlers('reproductive')" class="organ-group" :class="organClass('reproductive')">
          <ellipse cx="210" cy="524" rx="30" ry="26"/>
        </g>

        <!-- IMMUNE: spleen + lymph nodes -->
        <g v-bind="organHandlers('immune')" class="organ-group" :class="organClass('immune')">
          <ellipse cx="154" cy="358" rx="20" ry="24"/>
          <ellipse cx="150" cy="215" rx="8"  ry="8"/>
          <ellipse cx="270" cy="215" rx="8"  ry="8"/>
        </g>

      </g>
    </svg>

  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Effect } from '../api/client'

export type ViewMode = 'benefits' | 'side_effects' | 'both' | 'neutral'

const props = defineProps<{
  effects: Effect[]
  hovered: string | null
  viewMode: ViewMode
  reduceMotion?: boolean
  showToggle?: boolean
  benefitCount?: number
  sideCount?: number
}>()

const emit = defineEmits<{
  'update:hovered':  [value: string | null]
  'update:viewMode': [value: ViewMode]
}>()

const modeOpts = computed(() => [
  { value: 'neutral'      as ViewMode, label: 'Overview',     color: '#60a5fa', count: undefined,          disabled: false },
  { value: 'benefits'     as ViewMode, label: 'Benefits',     color: '#4ade80', count: props.benefitCount, disabled: (props.benefitCount ?? 0) === 0 },
  { value: 'both'         as ViewMode, label: 'Both',         color: '#facc15', count: undefined,          disabled: false },
  { value: 'side_effects' as ViewMode, label: 'Side Effects', color: '#ff2020', count: props.sideCount,    disabled: (props.sideCount ?? 0) === 0 },
])

const effectMap = computed(() => {
  const map = new Map<string, Effect[]>()
  for (const e of props.effects) {
    if (!matchesMode(e)) continue
    if (!map.has(e.body_part)) map.set(e.body_part, [])
    map.get(e.body_part)!.push(e)
  }
  return map
})

function matchesMode(e: Effect): boolean {
  if (props.viewMode === 'both' || props.viewMode === 'neutral') return true
  if (props.viewMode === 'benefits') return e.effect_type === 'benefit'
  return e.effect_type === 'side_effect'
}
function effectsAt(p: string): Effect[] { return effectMap.value.get(p) ?? [] }
function maxSeverity(p: string): number {
  return effectsAt(p).reduce((acc, e) => Math.max(acc, ({ high:3, medium:2, low:1, unknown:0 }[e.severity as string] ?? 0)), 0)
}
function highlightType(p: string): 'none'|'benefit'|'side'|'both'|'neutral' {
  const fx = effectsAt(p); if (!fx.length) return 'none'
  if (props.viewMode === 'neutral') return 'neutral'
  const hasB  = fx.some(e => e.effect_type === 'benefit')
  const hasSE = fx.some(e => e.effect_type === 'side_effect')
  return hasB && hasSE ? 'both' : hasB ? 'benefit' : 'side'
}
function organClass(p: string) {
  const hl = highlightType(p)
  return [
    `hl-${hl}`,
    props.hovered === p ? 'hovered' : '',
    props.hovered && props.hovered !== p ? 'dim' : '',
    maxSeverity(p) >= 3 && !props.reduceMotion ? 'pulse-strong' : '',
    hl === 'none' ? 'inactive' : '',
  ]
}
function organStroke(p: string): string {
  const hl = highlightType(p)
  return hl==='benefit'?'#4ade80': hl==='side'?'#ff2020': hl==='both'?'#facc15': hl==='neutral'?'#60a5fa':'transparent'
}
function organHandlers(p: string) {
  return {
    onMouseenter: () => emit('update:hovered', p),
    onMouseleave: () => emit('update:hovered', null),
    onFocus:      () => emit('update:hovered', p),
    onBlur:       () => emit('update:hovered', null),
    tabindex: highlightType(p) === 'none' ? -1 : 0,
    role: 'button', 'aria-label': `${p} region`,
  }
}

const hoveredColor = computed(() => {
  if (!props.hovered) return '#94a3b8'
  const hl = highlightType(props.hovered)
  return hl === 'benefit' ? '#4ade80' : hl === 'side' ? '#ff2020' : hl === 'both' ? '#facc15' : hl === 'neutral' ? '#60a5fa' : '#c9a84c'
})

const bpLabels: Record<string, string> = {
  brain: 'Brain', eye: 'Eyes', ear: 'Ears', heart: 'Heart',
  lung: 'Lungs', liver: 'Liver', stomach: 'Stomach', kidney: 'Kidneys',
  skin: 'Skin', muscle: 'Muscles', blood: 'Blood System',
  vascular: 'Vascular System', endocrine: 'Endocrine System',
  reproductive: 'Reproductive System', immune: 'Immune System',
}
function bodyPartLabel(p: string): string {
  return bpLabels[p] ?? (p.charAt(0).toUpperCase() + p.slice(1))
}
</script>

<style scoped>
.anatomy-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  user-select: none;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

/* Toggle (same as AnatomyBody) */
.mode-toggle { display: flex; gap: 6px; padding: 4px; background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; }
.mode-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 14px; background: transparent; border: none;
  color: #94a3b8; font-size: .82rem; font-weight: 500; border-radius: 8px;
  cursor: pointer; transition: background .15s, color .15s;
}
.mode-btn:hover:not(:disabled) { background: #1e293b; color: #e2e8f0; }
.mode-active { background: #1e293b; color: #f1f5f9; }
.mode-active.mode-neutral      { box-shadow: inset 0 0 0 1px #1d4ed8; color: #60a5fa; }
.mode-active.mode-benefits     { box-shadow: inset 0 0 0 1px #16a34a; color: #4ade80; }
.mode-active.mode-side_effects { box-shadow: inset 0 0 0 1px #cc0000; color: #ff2020; }
.mode-active.mode-both         { box-shadow: inset 0 0 0 1px #b45309; color: #facc15; }
.mode-disabled { opacity: 0.35; cursor: not-allowed; }
.mode-dot { width: 8px; height: 8px; border-radius: 50%; }
.mode-count { background: rgba(255,255,255,.06); padding: 1px 6px; border-radius: 8px; font-size: .68rem; }

.anatomy-svg {
  width: 100%;
  height: 100%;
  flex: 1;
  min-height: 0;
  overflow: visible;
}

/* ── Organ glow ellipses ── */
.organ-group {
  fill: white;
  opacity: 0.0;
  cursor: pointer;
  outline: none;
  transition: fill 0.25s, opacity 0.25s, filter 0.3s;
}

/* Inactive (no data) */
.organ-group.inactive  { cursor: default; opacity: 0 !important; }
.organ-group.hl-none   { opacity: 0; }

/* Dim when other is hovered */
.organ-group.dim { opacity: 0.02 !important; filter: none !important; }

/* Skin is a large background area — keep very subtle */
.skin-group { opacity: 0 !important; }
.skin-group.hl-benefit,
.skin-group.hl-side,
.skin-group.hl-both,
.skin-group.hl-neutral { opacity: 0.06 !important; }
.skin-group.hovered,
.skin-group:not(.inactive):hover { opacity: 0.10 !important; }

/* Highlight states */
.organ-group.hl-benefit {
  fill: #4ade80;
  opacity: 0.25;
  filter: drop-shadow(0 0 14px rgba(74,222,128,.9))
          drop-shadow(0 0 5px rgba(74,222,128,.5));
}
.organ-group.hl-side {
  fill: #ff2020;
  opacity: 0.25;
  filter: drop-shadow(0 0 14px rgba(255,32,32,.9))
          drop-shadow(0 0 5px rgba(255,32,32,.5));
}
.organ-group.hl-both {
  fill: #facc15;
  opacity: 0.25;
  filter: drop-shadow(0 0 14px rgba(250,204,21,.9))
          drop-shadow(0 0 5px rgba(250,204,21,.5));
}
.organ-group.hl-neutral {
  fill: #60a5fa;
  opacity: 0.18;
  filter: drop-shadow(0 0 14px rgba(96,165,250,.85))
          drop-shadow(0 0 5px rgba(96,165,250,.4));
}

/* Hover boost */
.organ-group.hl-benefit.hovered,
.organ-group.hl-benefit:not(.inactive):hover {
  opacity: 0.45;
  filter: drop-shadow(0 0 22px rgba(74,222,128,1))
          drop-shadow(0 0 10px rgba(74,222,128,.65));
}
.organ-group.hl-side.hovered,
.organ-group.hl-side:not(.inactive):hover {
  opacity: 0.45;
  filter: drop-shadow(0 0 22px rgba(255,32,32,1))
          drop-shadow(0 0 10px rgba(255,32,32,.65));
}
.organ-group.hl-both.hovered,
.organ-group.hl-both:not(.inactive):hover {
  opacity: 0.45;
  filter: drop-shadow(0 0 22px rgba(250,204,21,1))
          drop-shadow(0 0 10px rgba(250,204,21,.65));
}
.organ-group.hl-neutral.hovered,
.organ-group.hl-neutral:not(.inactive):hover {
  opacity: 0.38;
  filter: drop-shadow(0 0 22px rgba(96,165,250,1))
          drop-shadow(0 0 10px rgba(96,165,250,.65));
}

/* Pulse animation for high-severity organs */
@keyframes pulse-glow-benefit {
  0%,100% { filter: drop-shadow(0 0 14px rgba(74,222,128,.9)); }
  50%     { filter: drop-shadow(0 0 26px rgba(74,222,128,1)) drop-shadow(0 0 12px rgba(74,222,128,.7)); }
}
@keyframes pulse-glow-side {
  0%,100% { filter: drop-shadow(0 0 14px rgba(255,32,32,.9)); }
  50%     { filter: drop-shadow(0 0 26px rgba(255,32,32,1)) drop-shadow(0 0 12px rgba(255,32,32,.7)); }
}
@keyframes pulse-glow-both {
  0%,100% { filter: drop-shadow(0 0 14px rgba(250,204,21,.9)); }
  50%     { filter: drop-shadow(0 0 26px rgba(250,204,21,1)) drop-shadow(0 0 12px rgba(250,204,21,.7)); }
}
@keyframes pulse-glow-neutral {
  0%,100% { filter: drop-shadow(0 0 14px rgba(96,165,250,.85)); }
  50%     { filter: drop-shadow(0 0 26px rgba(96,165,250,1)) drop-shadow(0 0 12px rgba(96,165,250,.7)); }
}
.pulse-strong.hl-benefit { animation: pulse-glow-benefit 1.8s ease-in-out infinite; }
.pulse-strong.hl-side    { animation: pulse-glow-side    1.8s ease-in-out infinite; }
.pulse-strong.hl-both    { animation: pulse-glow-both    1.8s ease-in-out infinite; }
.pulse-strong.hl-neutral { animation: pulse-glow-neutral 1.8s ease-in-out infinite; }

/* Reduced motion */
.reduce-motion .pulse-strong { animation: none !important; }
@media (prefers-reduced-motion: reduce) { .pulse-strong { animation: none !important; } }
</style>
