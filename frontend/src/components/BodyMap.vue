<!--
  BodyMap.vue — Vis 1 transparent body highlight (revised)

  Changes:
  - Bezier curve paths replace rectangles/ellipses for a more natural body outline
  - Organs placed at anatomically accurate positions
  - drop-shadow CSS glow (Safari-compatible)
  - Defaults to showing side effects (benefit data is sparse)
  - Inactive organ opacity raised to 0.15
-->
<template>
  <div class="body-map" :class="{ 'reduce-motion': reduceMotion }">

    <svg viewBox="0 0 240 520" xmlns="http://www.w3.org/2000/svg" class="body-svg">
      <!-- ── Body outline (decorative, non-interactive) ── -->
      <!-- Head -->
      <ellipse cx="120" cy="52" rx="38" ry="42" class="body-base"/>
      <!-- Neck -->
      <rect x="109" y="91" width="22" height="20" rx="5" class="body-base"/>
      <!-- Torso (curved path) -->
      <path d="M70 110 Q50 125 46 210 Q44 250 68 258 L120 264 L172 258 Q196 250 194 210 Q190 125 170 110 Q148 104 120 102 Q92 104 70 110 Z"
            class="body-base"/>
      <!-- Left arm -->
      <path d="M68 118 Q42 138 34 210 Q30 240 36 265 Q40 280 46 265 Q50 240 52 210 Q58 148 76 128 Z"
            class="body-base"/>
      <!-- Right arm -->
      <path d="M172 118 Q198 138 206 210 Q210 240 204 265 Q200 280 194 265 Q190 240 188 210 Q182 148 164 128 Z"
            class="body-base"/>
      <!-- Left leg -->
      <path d="M72 258 Q64 295 60 360 Q56 405 60 450 Q63 470 72 450 Q76 415 78 360 Q80 300 88 262 Z"
            class="body-base"/>
      <!-- Right leg -->
      <path d="M168 258 Q176 295 180 360 Q184 405 180 450 Q177 470 168 450 Q164 415 162 360 Q160 300 152 262 Z"
            class="body-base"/>

      <!-- ── Organ regions (interactive, show highlight) ── -->

      <!-- Brain -->
      <ellipse cx="120" cy="42" rx="28" ry="28"
               v-bind="regionAttrs('brain')"
               @mouseenter="$emit('update:hovered','brain')"
               @mouseleave="$emit('update:hovered',null)"/>

      <!-- Eyes (combined as one clickable region) -->
      <ellipse cx="106" cy="38" rx="6" ry="5"
               v-bind="regionAttrs('eye')"
               @mouseenter="$emit('update:hovered','eye')"
               @mouseleave="$emit('update:hovered',null)"/>
      <ellipse cx="134" cy="38" rx="6" ry="5"
               v-bind="regionAttrs('eye')"
               @mouseenter="$emit('update:hovered','eye')"
               @mouseleave="$emit('update:hovered',null)"/>

      <!-- Heart (left-center chest) -->
      <ellipse cx="106" cy="152" rx="18" ry="20"
               v-bind="regionAttrs('heart')"
               @mouseenter="$emit('update:hovered','heart')"
               @mouseleave="$emit('update:hovered',null)"/>

      <!-- Left lung -->
      <ellipse cx="88"  cy="148" rx="20" ry="30"
               v-bind="regionAttrs('lung')"
               @mouseenter="$emit('update:hovered','lung')"
               @mouseleave="$emit('update:hovered',null)"/>
      <!-- Right lung -->
      <ellipse cx="152" cy="148" rx="20" ry="30"
               v-bind="regionAttrs('lung')"
               @mouseenter="$emit('update:hovered','lung')"
               @mouseleave="$emit('update:hovered',null)"/>

      <!-- Liver (upper right abdomen) -->
      <ellipse cx="144" cy="192" rx="24" ry="16"
               v-bind="regionAttrs('liver')"
               @mouseenter="$emit('update:hovered','liver')"
               @mouseleave="$emit('update:hovered',null)"/>

      <!-- Stomach (centre abdomen) -->
      <ellipse cx="112" cy="208" rx="22" ry="16"
               v-bind="regionAttrs('stomach')"
               @mouseenter="$emit('update:hovered','stomach')"
               @mouseleave="$emit('update:hovered',null)"/>

      <!-- Left kidney -->
      <ellipse cx="88"  cy="225" rx="11" ry="17"
               v-bind="regionAttrs('kidney')"
               @mouseenter="$emit('update:hovered','kidney')"
               @mouseleave="$emit('update:hovered',null)"/>
      <!-- Right kidney -->
      <ellipse cx="152" cy="225" rx="11" ry="17"
               v-bind="regionAttrs('kidney')"
               @mouseenter="$emit('update:hovered','kidney')"
               @mouseleave="$emit('update:hovered',null)"/>

      <!-- Muscle / spine (lower torso) -->
      <ellipse cx="120" cy="244" rx="32" ry="16"
               v-bind="regionAttrs('muscle')"
               @mouseenter="$emit('update:hovered','muscle')"
               @mouseleave="$emit('update:hovered',null)"/>

      <!-- Blood / vascular (arm vessels) -->
      <rect x="32"  y="130" width="16" height="100" rx="7"
            v-bind="regionAttrs('blood')"
            @mouseenter="$emit('update:hovered','blood')"
            @mouseleave="$emit('update:hovered',null)"/>
      <rect x="192" y="130" width="16" height="100" rx="7"
            v-bind="regionAttrs('blood')"
            @mouseenter="$emit('update:hovered','blood')"
            @mouseleave="$emit('update:hovered',null)"/>

      <!-- Skin (thin outer highlight on head) -->
      <ellipse cx="120" cy="52" rx="36" ry="41"
               v-bind="regionAttrs('skin')"
               @mouseenter="$emit('update:hovered','skin')"
               @mouseleave="$emit('update:hovered',null)"/>

      <!-- Hovered organ label -->
      <text v-if="hovered" x="120" y="500"
            text-anchor="middle" class="hover-label">
        {{ hovered }}
      </text>
    </svg>

    <!-- No data overlay -->
    <div v-if="!effects.length" class="no-data-banner">
      <span class="no-data-icon">⚠</span>
      No FAERS adverse event data available for this drug
    </div>

    <!-- Legend -->
    <div class="legend" v-else>
      <span class="leg-dot benefit">●</span> Benefit
      <span class="leg-dot side-effect">●</span> Side Effect
      <span class="leg-dot inactive">●</span> No data
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Effect } from '../api/client'

const props = defineProps<{
  effects: Effect[]
  hovered: string | null
  reduceMotion?: boolean
}>()

defineEmits<{ 'update:hovered': [value: string | null] }>()

const effectMap = computed(() => {
  const map = new Map<string, Effect[]>()
  for (const e of props.effects) {
    if (!map.has(e.body_part)) map.set(e.body_part, [])
    map.get(e.body_part)!.push(e)
  }
  return map
})

function regionAttrs(bodyPart: string) {
  const effects = effectMap.value.get(bodyPart) ?? []
  const isHovered  = props.hovered === bodyPart
  const otherHover = props.hovered && props.hovered !== bodyPart

  if (!effects.length) {
    return {
      class: ['organ', 'organ-inactive', isHovered ? 'organ-focused' : ''],
      style: { opacity: otherHover ? 0.04 : 0.15 },
    }
  }

  const hasSE  = effects.some(e => e.effect_type === 'side_effect')
  const hasB   = effects.some(e => e.effect_type === 'benefit')
  const colorClass = hasSE && hasB ? 'organ-mixed'
                   : hasSE         ? 'organ-se'
                   :                 'organ-benefit'

  const maxSev = effects.reduce((acc, e) => {
    const r = { high: 3, medium: 2, low: 1, unknown: 0 }
    return Math.max(acc, r[e.severity as keyof typeof r] ?? 0)
  }, 0)

  const glowSize = maxSev >= 3 ? '12px' : maxSev >= 2 ? '7px' : '4px'
  const glowColor = hasSE ? '#f87171' : '#4ade80'

  return {
    class: ['organ', colorClass, isHovered ? 'organ-focused' : '',
            maxSev >= 3 && !props.reduceMotion ? 'organ-pulse' : ''],
    style: {
      opacity:    isHovered ? 1 : otherHover ? 0.25 : 0.82,
      filter:     `drop-shadow(0 0 ${glowSize} ${glowColor})`,
      transition: 'opacity .3s, filter .3s',
    },
  }
}
</script>

<style scoped>
.body-map {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  user-select: none;
}
.body-svg { width: 100%; max-width: 260px; height: auto; }

.body-base {
  fill: #1e293b;
  stroke: #334155;
  stroke-width: 1.5;
}

.organ {
  cursor: pointer;
  transition: opacity .3s, filter .3s;
  fill-opacity: 0.9;
}
.organ-inactive  { fill: #475569; }
.organ-se        { fill: #f87171; }
.organ-benefit   { fill: #4ade80; }
.organ-mixed     { fill: #fbbf24; }
.organ-focused   { stroke: #fff; stroke-width: 2; }
@keyframes bm-pulse {
  0%,100% { opacity: .85; }
  50%      { opacity: 1; filter: drop-shadow(0 0 10px currentColor); }
}
.organ-pulse     { animation: bm-pulse 1.8s ease-in-out infinite; }

.reduce-motion .organ { animation: none !important; transition: none !important; }

.hover-label {
  fill: #94a3b8;
  font-size: 13px;
  font-family: sans-serif;
  text-transform: capitalize;
}

.legend {
  display: flex;
  gap: 18px;
  font-size: 0.78rem;
  color: #64748b;
}
.leg-dot { font-size: .95rem; margin-right: 3px; }
.leg-dot.benefit     { color: #4ade80; }
.leg-dot.side-effect { color: #f87171; }
.leg-dot.inactive    { color: #475569; }

.no-data-banner {
  font-size: .78rem;
  color: #64748b;
  background: rgba(71,85,105,.12);
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 8px 16px;
  text-align: center;
  margin-top: 8px;
}
.no-data-icon { margin-right: 6px; }
</style>
