<!--
  CorpusWordCloud.vue — Body-mapped patient symptom atlas (v2.0)

  Renders the corpus-wide TF-IDF terms from /api/corpus/nlp as an SVG word
  cloud where each of the 15 body systems has its own placement zone and
  color. The body silhouette (same skin path used by AnatomyBody.vue) sits
  in the center; small / location-sensitive organs (eye, ear, vascular,
  endocrine, blood, immune) get callout zones on either side of the figure.

  Words are sized by score_norm (TF-IDF) and placed by greedy spiral packing
  within each organ's zone — see utils/wordCloudLayout.ts.
-->

<template>
  <div class="wc-wrap" :class="{ 'is-loading': loading, 'is-error': hasError }">
    <svg
      viewBox="0 0 420 780"
      class="wc-svg"
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label="Patient vocabulary mapped to body systems"
    >
      <defs>
        <linearGradient id="wc-body-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stop-color="#1a1f3a" stop-opacity="0.55"/>
          <stop offset="55%"  stop-color="#0d1124" stop-opacity="0.35"/>
          <stop offset="100%" stop-color="#06080f" stop-opacity="0.15"/>
        </linearGradient>

        <filter id="wc-word-glow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="0.6" result="b"/>
          <feMerge>
            <feMergeNode in="b"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
      </defs>

      <!-- ── Layer 1: Body silhouette ─────────────────────────────────── -->
      <g class="wc-silhouette">
        <path :d="BODY_SILHOUETTE_PATH" fill="url(#wc-body-fill)"/>
        <path
          :d="BODY_SILHOUETTE_PATH"
          fill="none"
          stroke="#c9a84c"
          stroke-width="1.3"
          opacity="0.42"
        />
      </g>

      <!-- ── Layer 2: Frames + connector lines + words ────────────────── -->
      <g class="wc-words">
        <g
          v-for="organ in ORGANS"
          :key="organ.key"
          :class="['organ-group', `og-${organ.key}`, { dim: dimOthers(organ.key), empty: !(layouts.get(organ.key)?.length) }]"
          @mouseenter="hoveredOrgan = organ.key"
          @mouseleave="hoveredOrgan = null"
        >
          <!-- Connector line: box edge → body anchor (skipped if anchor sits inside the box) -->
          <line
            v-if="connectors.get(organ.key)"
            :x1="connectors.get(organ.key)!.x1"
            :y1="connectors.get(organ.key)!.y1"
            :x2="connectors.get(organ.key)!.x2"
            :y2="connectors.get(organ.key)!.y2"
            :stroke="organ.color"
            stroke-width="0.7"
            stroke-dasharray="1.6 2"
            opacity="0.55"
            class="wc-connector"
          />

          <!-- Anchor dot on the body -->
          <circle
            :cx="organ.anchor.x"
            :cy="organ.anchor.y"
            r="2.6"
            :fill="organ.color"
            opacity="0.78"
            class="wc-anchor-dot"
          />
          <circle
            :cx="organ.anchor.x"
            :cy="organ.anchor.y"
            r="1.2"
            fill="#05080f"
            opacity="0.7"
          />

          <!-- Frame around this organ's word cloud -->
          <rect
            :x="organ.zone.x"
            :y="organ.zone.y"
            :width="organ.zone.w"
            :height="organ.zone.h"
            :fill="organ.color"
            fill-opacity="0.035"
            :stroke="organ.color"
            stroke-width="0.7"
            stroke-opacity="0.42"
            rx="4"
            class="wc-frame"
          />

          <!-- Frame label tag -->
          <text
            :x="organ.zone.x + 6"
            :y="organ.zone.y - 3"
            :fill="organ.color"
            opacity="0.78"
            font-family="'IBM Plex Mono', monospace"
            font-size="6.5"
            font-weight="700"
            letter-spacing="1.2"
            class="wc-frame-label"
          >{{ organ.label.toUpperCase() }}</text>

          <!-- Words -->
          <text
            v-for="w in (layouts.get(organ.key) ?? [])"
            :key="`${organ.key}-${w.term}`"
            :x="w.x"
            :y="w.y"
            :fill="organ.color"
            :opacity="w.opacity"
            :font-size="w.fontSize"
            font-family="'Playfair Display', Georgia, serif"
            font-weight="600"
            text-anchor="middle"
            dominant-baseline="middle"
            filter="url(#wc-word-glow)"
            class="wc-word"
          >
            <title>{{ w.term }} · {{ organ.label }} · rank #{{ w.rank }}</title>
            {{ w.term }}
          </text>
        </g>
      </g>

      <!-- ── States ───────────────────────────────────────────────────── -->
      <text
        v-if="loading"
        x="210" y="395"
        fill="#b0a898" opacity="0.6"
        font-family="'IBM Plex Mono', monospace" font-size="9"
        letter-spacing="2"
        text-anchor="middle"
      >LOADING PATIENT VOCABULARY…</text>

      <text
        v-if="hasError"
        x="210" y="395"
        fill="#ef4444" opacity="0.75"
        font-family="'IBM Plex Mono', monospace" font-size="9"
        letter-spacing="2"
        text-anchor="middle"
      >FAILED TO LOAD CORPUS DATA</text>
    </svg>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api/client'
import {
  ORGANS,
  BODY_SILHOUETTE_PATH,
  type OrganKey,
  type Zone,
} from '../data/anatomyOrgans'
import {
  placeWordsInBBox,
  type PlacedWord,
  type InputWord,
} from '../utils/wordCloudLayout'

interface Connector { x1: number; y1: number; x2: number; y2: number }

const loading       = ref(true)
const hasError      = ref(false)
const hoveredOrgan  = ref<OrganKey | null>(null)
const layouts       = ref<Map<OrganKey, PlacedWord[]>>(new Map())

// Pre-compute connector lines once — zones and anchors are static.
const connectors = new Map<OrganKey, Connector | null>(
  ORGANS.map(o => [o.key, connectorLine(o.zone, o.anchor)]),
)

function dimOthers(key: OrganKey): boolean {
  return hoveredOrgan.value !== null && hoveredOrgan.value !== key
}

/** Line from the zone-rect's nearest edge to the body anchor point.
 *  Returns null when the anchor sits inside the zone (no connector needed). */
function connectorLine(zone: Zone, a: { x: number; y: number }): Connector | null {
  if (a.x >= zone.x && a.x <= zone.x + zone.w
   && a.y >= zone.y && a.y <= zone.y + zone.h) return null

  const cx = zone.x + zone.w / 2
  const cy = zone.y + zone.h / 2
  const dx = a.x - cx
  const dy = a.y - cy
  const tRight  = dx > 0 ? (zone.x + zone.w - cx) / dx : Infinity
  const tLeft   = dx < 0 ? (zone.x          - cx) / dx : Infinity
  const tBottom = dy > 0 ? (zone.y + zone.h - cy) / dy : Infinity
  const tTop    = dy < 0 ? (zone.y          - cy) / dy : Infinity
  const t = Math.min(tRight, tLeft, tBottom, tTop)
  return { x1: cx + t * dx, y1: cy + t * dy, x2: a.x, y2: a.y }
}

onMounted(async () => {
  try {
    const res = await api.getCorpusNlp()
    if (!res?.data?.success) { hasError.value = true; return }
    const tfidf = res.data.data.tfidf as Record<string, InputWord[]>

    const map = new Map<OrganKey, PlacedWord[]>()
    for (const organ of ORGANS) {
      const words = tfidf[organ.key] ?? []
      if (!words.length) continue
      const placed = placeWordsInBBox(
        organ.zone,
        words,
        {
          maxWords:    organ.maxWords,
          minFontSize: 8,
          maxFontSize: organ.zone.w >= 100 ? 19 : 14,
        },
      )
      if (placed.length) map.set(organ.key, placed)
    }
    layouts.value = map
  } catch (e) {
    console.error('CorpusWordCloud: failed to load corpus NLP', e)
    hasError.value = true
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.wc-wrap {
  width: 100%;
  display: flex;
  justify-content: center;
  position: relative;
}

.wc-svg {
  width: 100%;
  max-width: 520px;
  aspect-ratio: 420 / 780;
  display: block;
  filter: drop-shadow(0 6px 24px rgba(0, 0, 0, 0.42));
}

.organ-group {
  cursor: pointer;
  transition: opacity 0.22s ease;
}
.organ-group.dim   { opacity: 0.18; }
.organ-group.empty { display: none; }

.wc-word, .wc-frame, .wc-connector, .wc-frame-label, .wc-anchor-dot {
  transition: opacity 0.18s ease;
}
</style>
