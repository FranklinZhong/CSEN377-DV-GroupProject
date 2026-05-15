<!--
  AnatomyBody.vue — Vis 1 interactive anatomy figure (v3.5, replaces BodyMap.vue)

  - Anatomical-style SVG: skin gradient + solid organs + vascular texture + breathing/heartbeat animations
  - viewMode = 'benefits' | 'side_effects' | 'both' → switches highlight color scheme
  - Accepts effects: Effect[]; highlight intensity per organ is determined by body_part
  - Hover emits ('update:hovered', body_part)
  - Respects prefers-reduced-motion
-->
<template>
  <div class="anatomy-wrap" :class="{ 'reduce-motion': reduceMotion }">
    <!-- View Mode Toggle -->
    <div class="mode-toggle" v-if="showToggle">
      <button
        v-for="opt in modeOpts"
        :key="opt.value"
        class="mode-btn"
        :class="[
          `mode-${opt.value}`,
          { 'mode-active': viewMode === opt.value, 'mode-disabled': opt.disabled }
        ]"
        :disabled="opt.disabled"
        :title="opt.disabled ? 'No data available' : ''"
        @click="$emit('update:viewMode', opt.value)"
      >
        <span class="mode-dot" :style="{ background: opt.color }"></span>
        {{ opt.label }}
        <span v-if="opt.count" class="mode-count">{{ opt.count }}</span>
      </button>
    </div>

    <svg viewBox="0 0 260 540" xmlns="http://www.w3.org/2000/svg" class="anatomy-svg">
      <defs>
        <!-- skin gradient -->
        <linearGradient id="skin-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"  stop-color="#1e293b" stop-opacity="0.85"/>
          <stop offset="50%" stop-color="#172033" stop-opacity="0.92"/>
          <stop offset="100%" stop-color="#0f172a" stop-opacity="0.98"/>
        </linearGradient>
        <radialGradient id="head-grad" cx="0.5" cy="0.4" r="0.7">
          <stop offset="0%" stop-color="#26334a"/>
          <stop offset="100%" stop-color="#0f172a"/>
        </radialGradient>

        <!-- organ gradients (resting state — soft, low saturation) -->
        <radialGradient id="brain-grad" cx="0.4" cy="0.35" r="0.7">
          <stop offset="0%"  stop-color="#a78bfa" stop-opacity="0.75"/>
          <stop offset="100%" stop-color="#5b21b6" stop-opacity="0.4"/>
        </radialGradient>
        <radialGradient id="heart-grad" cx="0.4" cy="0.4" r="0.65">
          <stop offset="0%"  stop-color="#f87171" stop-opacity="0.85"/>
          <stop offset="100%" stop-color="#7f1d1d" stop-opacity="0.5"/>
        </radialGradient>
        <radialGradient id="lung-grad" cx="0.5" cy="0.3" r="0.8">
          <stop offset="0%"  stop-color="#38bdf8" stop-opacity="0.55"/>
          <stop offset="100%" stop-color="#0c4a6e" stop-opacity="0.3"/>
        </radialGradient>
        <radialGradient id="liver-grad" cx="0.3" cy="0.3" r="0.8">
          <stop offset="0%"  stop-color="#fbbf24" stop-opacity="0.65"/>
          <stop offset="100%" stop-color="#78350f" stop-opacity="0.4"/>
        </radialGradient>
        <radialGradient id="stomach-grad" cx="0.4" cy="0.3" r="0.8">
          <stop offset="0%"  stop-color="#fb923c" stop-opacity="0.7"/>
          <stop offset="100%" stop-color="#7c2d12" stop-opacity="0.4"/>
        </radialGradient>
        <radialGradient id="kidney-grad" cx="0.4" cy="0.4" r="0.7">
          <stop offset="0%"  stop-color="#c084fc" stop-opacity="0.65"/>
          <stop offset="100%" stop-color="#4c1d95" stop-opacity="0.4"/>
        </radialGradient>
        <linearGradient id="muscle-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#fb7185" stop-opacity="0.4"/>
          <stop offset="100%" stop-color="#881337" stop-opacity="0.25"/>
        </linearGradient>

        <!-- highlight tints applied via fill-opacity overlay -->
        <radialGradient id="hl-benefit" cx="0.5" cy="0.5" r="0.7">
          <stop offset="0%"  stop-color="#4ade80" stop-opacity="1"/>
          <stop offset="100%" stop-color="#16a34a" stop-opacity="0.5"/>
        </radialGradient>
        <radialGradient id="hl-side" cx="0.5" cy="0.5" r="0.7">
          <stop offset="0%"  stop-color="#f87171" stop-opacity="1"/>
          <stop offset="100%" stop-color="#dc2626" stop-opacity="0.55"/>
        </radialGradient>
        <radialGradient id="hl-both" cx="0.5" cy="0.5" r="0.7">
          <stop offset="0%"  stop-color="#facc15" stop-opacity="1"/>
          <stop offset="100%" stop-color="#b45309" stop-opacity="0.55"/>
        </radialGradient>

        <!-- glow filter -->
        <filter id="glow-soft" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="2.5" result="b"/>
          <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
        <filter id="glow-strong" x="-100%" y="-100%" width="300%" height="300%">
          <feGaussianBlur stdDeviation="5" result="b"/>
          <feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
      </defs>

      <!-- ── Layer 1: Body silhouette (decorative, non-interactive) ── -->
      <g class="silhouette">
        <!-- head -->
        <ellipse cx="130" cy="56" rx="42" ry="46" fill="url(#head-grad)" stroke="#334155" stroke-width="1"/>
        <!-- neck -->
        <path d="M115 98 Q115 110 118 116 L142 116 Q145 110 145 98 Z" fill="url(#skin-grad)" stroke="#334155" stroke-width="1"/>
        <!-- shoulders + torso -->
        <path
          d="M70 122 Q60 128 56 145
             L42 188 Q38 240 64 256
             L78 268 L86 280 Q90 320 88 350
             L86 410 Q84 440 82 480 L88 510 L100 512 L108 480 Q108 440 110 410
             Q112 360 116 320 L116 280 L144 280 L144 320 Q148 360 150 410
             Q152 440 152 480 L160 512 L172 510 L178 480 Q176 440 174 410 L172 350
             Q170 320 174 280 L182 268 L196 256 Q222 240 218 188
             L204 145 Q200 128 190 122
             Q160 110 130 110 Q100 110 70 122 Z"
          fill="url(#skin-grad)"
          stroke="#334155"
          stroke-width="1.2"
        />
        <!-- arms -->
        <path d="M58 144 Q40 158 30 220 Q26 260 32 290 Q38 308 44 300 Q46 280 50 250 Q56 200 70 158 Z"
              fill="url(#skin-grad)" stroke="#334155" stroke-width="1"/>
        <path d="M202 144 Q220 158 230 220 Q234 260 228 290 Q222 308 216 300 Q214 280 210 250 Q204 200 190 158 Z"
              fill="url(#skin-grad)" stroke="#334155" stroke-width="1"/>
      </g>

      <!-- ── Layer 2: Skeleton hints ── -->
      <g class="skeleton" opacity="0.18">
        <!-- ribs -->
        <path d="M82 158 Q130 152 178 158" stroke="#cbd5e1" stroke-width="1" fill="none"/>
        <path d="M78 175 Q130 168 182 175" stroke="#cbd5e1" stroke-width="1" fill="none"/>
        <path d="M76 192 Q130 185 184 192" stroke="#cbd5e1" stroke-width="1" fill="none"/>
        <path d="M78 210 Q130 203 182 210" stroke="#cbd5e1" stroke-width="1" fill="none"/>
        <!-- spine -->
        <line x1="130" y1="120" x2="130" y2="290" stroke="#cbd5e1" stroke-width="1.3"/>
        <line x1="130" y1="290" x2="125" y2="510" stroke="#cbd5e1" stroke-width="0.8"/>
        <line x1="130" y1="290" x2="135" y2="510" stroke="#cbd5e1" stroke-width="0.8"/>
      </g>

      <!-- ── Layer 3: Vascular system (decorative animation) ── -->
      <g class="vasculature" opacity="0.5">
        <!-- carotid arteries (heart → head) -->
        <path d="M124 152 Q120 130 122 110" stroke="#dc2626" stroke-width="1.5" fill="none" opacity="0.7"/>
        <path d="M136 152 Q140 130 138 110" stroke="#dc2626" stroke-width="1.5" fill="none" opacity="0.7"/>
        <!-- main aorta -->
        <path d="M130 165 Q130 200 130 250 Q128 290 126 340"
              stroke="#dc2626" stroke-width="2" fill="none" class="vessel-pulse"/>
        <!-- vena cava -->
        <path d="M134 165 Q134 200 134 250 Q132 290 130 340"
              stroke="#1e40af" stroke-width="2" fill="none" opacity="0.6"/>
        <!-- arm vessels -->
        <path d="M68 158 Q56 200 46 260" stroke="#dc2626" stroke-width="1" fill="none" opacity="0.5"/>
        <path d="M192 158 Q204 200 214 260" stroke="#dc2626" stroke-width="1" fill="none" opacity="0.5"/>
      </g>

      <!-- ── Layer 4: Organs (interactive) ── -->
      <g class="organs">
        <!-- Brain -->
        <g
          v-bind="organHandlers('brain')"
          class="organ-group"
          :class="organClass('brain')"
        >
          <ellipse cx="130" cy="46" rx="28" ry="26" fill="url(#brain-grad)"
                   :filter="organFilter('brain')"/>
          <!-- gyri stripes -->
          <path d="M108 42 Q122 36 134 42 Q146 36 154 44" stroke="#c4b5fd"
                stroke-width="0.7" fill="none" opacity="0.45"/>
          <path d="M108 52 Q122 46 134 52 Q146 46 154 54" stroke="#c4b5fd"
                stroke-width="0.7" fill="none" opacity="0.45"/>
        </g>

        <!-- Eyes -->
        <g v-bind="organHandlers('eye')" class="organ-group" :class="organClass('eye')">
          <ellipse cx="116" cy="44" rx="6" ry="4" fill="#e0e7ff" opacity="0.85"/>
          <ellipse cx="116" cy="44" rx="2.5" ry="2.5" fill="#0f172a"/>
          <ellipse cx="144" cy="44" rx="6" ry="4" fill="#e0e7ff" opacity="0.85"/>
          <ellipse cx="144" cy="44" rx="2.5" ry="2.5" fill="#0f172a"/>
        </g>

        <!-- Heart -->
        <g v-bind="organHandlers('heart')" class="organ-group heart-beat" :class="organClass('heart')">
          <path d="M122 142 C 114 132, 100 138, 104 154
                   C 108 168, 122 176, 130 182
                   C 138 176, 152 168, 156 154
                   C 160 138, 146 132, 138 142
                   C 134 138, 126 138, 122 142 Z"
                fill="url(#heart-grad)" :filter="organFilter('heart')"/>
        </g>

        <!-- Lungs -->
        <g v-bind="organHandlers('lung')" class="organ-group lung-breath" :class="organClass('lung')">
          <path d="M88 130 Q70 138 68 175 Q70 205 90 218 Q108 218 110 200 L110 140 Q104 128 88 130 Z"
                fill="url(#lung-grad)" :filter="organFilter('lung')"/>
          <path d="M172 130 Q190 138 192 175 Q190 205 170 218 Q152 218 150 200 L150 140 Q156 128 172 130 Z"
                fill="url(#lung-grad)" :filter="organFilter('lung')"/>
          <!-- bronchi -->
          <path d="M110 160 Q98 168 90 180" stroke="#bae6fd" stroke-width="0.8" fill="none" opacity="0.5"/>
          <path d="M150 160 Q162 168 170 180" stroke="#bae6fd" stroke-width="0.8" fill="none" opacity="0.5"/>
        </g>

        <!-- Liver -->
        <g v-bind="organHandlers('liver')" class="organ-group" :class="organClass('liver')">
          <path d="M88 222 Q86 218 100 218 L162 220 Q176 222 178 234
                   Q178 252 168 256 Q140 258 110 254 Q92 250 88 240 Z"
                fill="url(#liver-grad)" :filter="organFilter('liver')"/>
        </g>

        <!-- Stomach -->
        <g v-bind="organHandlers('stomach')" class="organ-group" :class="organClass('stomach')">
          <path d="M110 248 Q102 252 102 264 Q104 280 116 282 Q132 284 146 278
                   Q156 272 154 258 Q152 248 142 246 Q124 244 110 248 Z"
                fill="url(#stomach-grad)" :filter="organFilter('stomach')"/>
        </g>

        <!-- Kidneys -->
        <g v-bind="organHandlers('kidney')" class="organ-group" :class="organClass('kidney')">
          <ellipse cx="98" cy="266" rx="10" ry="16" fill="url(#kidney-grad)"
                   :filter="organFilter('kidney')"/>
          <ellipse cx="162" cy="266" rx="10" ry="16" fill="url(#kidney-grad)"
                   :filter="organFilter('kidney')"/>
        </g>

        <!-- Skin (head outer) -->
        <g v-bind="organHandlers('skin')" class="organ-group" :class="organClass('skin')">
          <ellipse cx="130" cy="56" rx="41" ry="45" fill="none"
                   :stroke="organStroke('skin')" stroke-width="2" opacity="0.6"/>
        </g>

        <!-- Muscle (lower torso & arms) -->
        <g v-bind="organHandlers('muscle')" class="organ-group" :class="organClass('muscle')">
          <path d="M96 290 L96 380 Q96 410 102 412 L116 412 Q120 380 118 320 L116 290 Z"
                fill="url(#muscle-grad)" :filter="organFilter('muscle')"/>
          <path d="M164 290 L164 380 Q164 410 158 412 L144 412 Q140 380 142 320 L144 290 Z"
                fill="url(#muscle-grad)" :filter="organFilter('muscle')"/>
        </g>

        <!-- Blood / vascular (highlight arms) -->
        <g v-bind="organHandlers('blood')" class="organ-group" :class="organClass('blood')">
          <ellipse cx="46" cy="222" rx="6" ry="22" fill="url(#heart-grad)" opacity="0.6"
                   :filter="organFilter('blood')"/>
          <ellipse cx="214" cy="222" rx="6" ry="22" fill="url(#heart-grad)" opacity="0.6"
                   :filter="organFilter('blood')"/>
        </g>

        <!-- Vascular (whole-body circulation, mapped to arms+legs) -->
        <g v-bind="organHandlers('vascular')" class="organ-group" :class="organClass('vascular')">
          <circle cx="130" cy="155" r="3" fill="none" :stroke="organStroke('vascular')"
                  stroke-width="2" :filter="organFilter('vascular')" opacity="0.7"/>
        </g>

        <!-- Endocrine (pituitary + thyroid + pancreas hint) -->
        <g v-bind="organHandlers('endocrine')" class="organ-group" :class="organClass('endocrine')">
          <circle cx="130" cy="68" r="3" fill="url(#brain-grad)" :filter="organFilter('endocrine')" opacity="0.85"/>
          <ellipse cx="130" cy="112" rx="6" ry="3" fill="url(#brain-grad)"
                   :filter="organFilter('endocrine')" opacity="0.7"/>
          <ellipse cx="130" cy="248" rx="10" ry="3" fill="url(#brain-grad)"
                   :filter="organFilter('endocrine')" opacity="0.65"/>
        </g>

        <!-- Reproductive -->
        <g v-bind="organHandlers('reproductive')" class="organ-group" :class="organClass('reproductive')">
          <ellipse cx="130" cy="320" rx="14" ry="8" fill="url(#stomach-grad)"
                   :filter="organFilter('reproductive')" opacity="0.55"/>
        </g>

        <!-- Immune (lymph nodes hint) -->
        <g v-bind="organHandlers('immune')" class="organ-group" :class="organClass('immune')">
          <circle cx="100" cy="120" r="2" fill="#a78bfa" :filter="organFilter('immune')" opacity="0.7"/>
          <circle cx="160" cy="120" r="2" fill="#a78bfa" :filter="organFilter('immune')" opacity="0.7"/>
          <circle cx="106" cy="232" r="2" fill="#a78bfa" :filter="organFilter('immune')" opacity="0.7"/>
          <circle cx="154" cy="232" r="2" fill="#a78bfa" :filter="organFilter('immune')" opacity="0.7"/>
        </g>

        <!-- Ear -->
        <g v-bind="organHandlers('ear')" class="organ-group" :class="organClass('ear')">
          <path d="M90 56 Q86 58 86 64 Q86 72 92 74" fill="none"
                :stroke="organStroke('ear')" stroke-width="2" opacity="0.75"
                :filter="organFilter('ear')"/>
          <path d="M170 56 Q174 58 174 64 Q174 72 168 74" fill="none"
                :stroke="organStroke('ear')" stroke-width="2" opacity="0.75"
                :filter="organFilter('ear')"/>
        </g>
      </g>

      <!-- Hovered label -->
      <text v-if="hovered" x="130" y="528"
            text-anchor="middle"
            fill="#cbd5e1"
            font-size="12"
            font-family="system-ui, sans-serif"
            class="hover-label">
        {{ hovered }}
      </text>
    </svg>

    <!-- Legend -->
    <div class="legend">
      <span class="leg" v-if="viewMode !== 'side_effects'">
        <i class="leg-dot benefit"></i> Benefit
      </span>
      <span class="leg" v-if="viewMode !== 'benefits'">
        <i class="leg-dot side"></i> Side Effect
      </span>
      <span class="leg" v-if="viewMode === 'both'">
        <i class="leg-dot both"></i> Both
      </span>
      <span class="leg leg-meta">{{ effectMap.size }} body regions affected</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Effect } from '../api/client'

export type ViewMode = 'benefits' | 'side_effects' | 'both'

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
  {
    value: 'benefits' as ViewMode,
    label: 'Benefits',
    color: '#4ade80',
    count: props.benefitCount,
    disabled: (props.benefitCount ?? 0) === 0,
  },
  {
    value: 'both' as ViewMode,
    label: 'Both',
    color: '#facc15',
    count: undefined,
    disabled: false,
  },
  {
    value: 'side_effects' as ViewMode,
    label: 'Side Effects',
    color: '#f87171',
    count: props.sideCount,
    disabled: (props.sideCount ?? 0) === 0,
  },
])

// Group effects by body_part — but filter by viewMode
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
  if (props.viewMode === 'both') return true
  if (props.viewMode === 'benefits') return e.effect_type === 'benefit'
  return e.effect_type === 'side_effect'
}

function effectsAt(bodyPart: string): Effect[] {
  return effectMap.value.get(bodyPart) ?? []
}

function maxSeverity(bodyPart: string): number {
  const fx = effectsAt(bodyPart)
  return fx.reduce((acc, e) => {
    const r = { high: 3, medium: 2, low: 1, unknown: 0 }
    return Math.max(acc, r[e.severity as keyof typeof r] ?? 0)
  }, 0)
}

function highlightType(bodyPart: string): 'none' | 'benefit' | 'side' | 'both' {
  const fx = effectsAt(bodyPart)
  if (!fx.length) return 'none'
  const hasB  = fx.some(e => e.effect_type === 'benefit')
  const hasSE = fx.some(e => e.effect_type === 'side_effect')
  if (hasB && hasSE) return 'both'
  if (hasB)  return 'benefit'
  return 'side'
}

function organClass(bodyPart: string) {
  const isHovered  = props.hovered === bodyPart
  const otherHover = props.hovered && props.hovered !== bodyPart
  const hl = highlightType(bodyPart)
  const sev = maxSeverity(bodyPart)
  return [
    `hl-${hl}`,
    isHovered  ? 'hovered'      : '',
    otherHover ? 'dim'          : '',
    sev >= 3 && !props.reduceMotion ? 'pulse-strong' : '',
    hl === 'none' ? 'inactive'  : '',
  ]
}

function organFilter(bodyPart: string): string {
  const hl = highlightType(bodyPart)
  if (hl === 'none') return ''
  const sev = maxSeverity(bodyPart)
  return sev >= 2 ? 'url(#glow-strong)' : 'url(#glow-soft)'
}

function organStroke(bodyPart: string): string {
  const hl = highlightType(bodyPart)
  if (hl === 'benefit') return '#4ade80'
  if (hl === 'side')    return '#f87171'
  if (hl === 'both')    return '#facc15'
  return '#475569'
}

function organHandlers(bodyPart: string) {
  return {
    onMouseenter: () => emit('update:hovered', bodyPart),
    onMouseleave: () => emit('update:hovered', null),
    onFocus:      () => emit('update:hovered', bodyPart),
    onBlur:       () => emit('update:hovered', null),
    tabindex: highlightType(bodyPart) === 'none' ? -1 : 0,
    role: 'button',
    'aria-label': `${bodyPart} region`,
  }
}
</script>

<style scoped>
.anatomy-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  user-select: none;
}

/* ── Toggle ───────────────────────────────────────────── */
.mode-toggle {
  display: flex;
  gap: 6px;
  padding: 4px;
  background: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 12px;
}
.mode-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: .82rem;
  font-weight: 500;
  border-radius: 8px;
  cursor: pointer;
  transition: background .15s, color .15s;
}
.mode-btn:hover:not(:disabled) {
  background: #1e293b;
  color: #e2e8f0;
}
.mode-active {
  background: #1e293b;
  color: #f1f5f9;
}
.mode-active.mode-benefits     { box-shadow: inset 0 0 0 1px #16a34a; color: #4ade80; }
.mode-active.mode-side_effects { box-shadow: inset 0 0 0 1px #dc2626; color: #f87171; }
.mode-active.mode-both         { box-shadow: inset 0 0 0 1px #b45309; color: #facc15; }
.mode-disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
.mode-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.mode-count {
  background: rgba(255,255,255,.06);
  padding: 1px 6px;
  border-radius: 8px;
  font-size: .68rem;
}

/* ── SVG ──────────────────────────────────────────────── */
.anatomy-svg {
  width: 100%;
  max-width: 320px;
  height: auto;
  display: block;
}

/* Heart beat */
.heart-beat {
  transform-origin: 130px 162px;
  animation: heart-pulse 1.2s ease-in-out infinite;
}
@keyframes heart-pulse {
  0%, 100% { transform: scale(1); }
  20%      { transform: scale(1.06); }
  40%      { transform: scale(0.98); }
  60%      { transform: scale(1.04); }
}

/* Lung breath */
.lung-breath {
  transform-origin: 130px 174px;
  animation: lung-breathe 4s ease-in-out infinite;
}
@keyframes lung-breathe {
  0%, 100% { transform: scale(1); }
  50%      { transform: scale(1.04); }
}

/* Vessel pulse */
.vessel-pulse {
  stroke-dasharray: 3 6;
  animation: vessel-flow 12s linear infinite;
}
@keyframes vessel-flow {
  0%   { stroke-dashoffset: 0; }
  100% { stroke-dashoffset: -200; }
}

/* Reduced motion */
.reduce-motion .heart-beat,
.reduce-motion .lung-breath,
.reduce-motion .vessel-pulse,
.reduce-motion .pulse-strong {
  animation: none !important;
}

/* Organ interaction */
.organ-group {
  cursor: pointer;
  transition: opacity .25s, transform .15s;
  outline: none;
}
.organ-group.inactive { cursor: default; }
.organ-group:not(.inactive):hover { transform: scale(1.04); transform-box: fill-box; transform-origin: center; }
.organ-group.hovered  { transform: scale(1.05); transform-box: fill-box; transform-origin: center; }
.organ-group.dim      { opacity: 0.35; }
.organ-group.inactive { opacity: 0.55; }

/* Highlight tints — via opacity boost since paint is gradient */
.organ-group.hl-benefit { filter: hue-rotate(80deg) saturate(1.4) brightness(1.05); }
.organ-group.hl-side    { /* native organ colors are already red-ish; keep */ }
.organ-group.hl-both    { filter: hue-rotate(35deg) saturate(1.3) brightness(1.1); }

@keyframes ab-pulse {
  0%, 100% { opacity: 0.9; }
  50%      { opacity: 1; filter: drop-shadow(0 0 12px currentColor); }
}
.pulse-strong { animation: ab-pulse 1.8s ease-in-out infinite; }

.hover-label {
  text-transform: capitalize;
  letter-spacing: 0.04em;
}

/* Legend */
.legend {
  display: flex;
  gap: 16px;
  font-size: .78rem;
  color: #64748b;
  align-items: center;
}
.leg { display: flex; align-items: center; gap: 5px; }
.leg-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.leg-dot.benefit { background: #4ade80; box-shadow: 0 0 6px #4ade80; }
.leg-dot.side    { background: #f87171; box-shadow: 0 0 6px #f87171; }
.leg-dot.both    { background: #facc15; box-shadow: 0 0 6px #facc15; }
.leg-meta { color: #475569; margin-left: auto; }
</style>
