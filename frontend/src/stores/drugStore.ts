import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { DrugSummary, DrugOverview, Effect, TrendPoint, ReviewCluster } from '../api/client'
import { api } from '../api/client'

export type EffectFilter = 'all' | 'benefits' | 'sideeffects' | 'high'
export type ViewMode = 'benefits' | 'side_effects' | 'both' | 'neutral'

export const useDrugStore = defineStore('drug', () => {
  // ── State ──────────────────────────────────────────────────────────────
  const currentDrug   = ref<DrugSummary | null>(null)
  const overview      = ref<DrugOverview | null>(null)
  const benefits      = ref<Effect[]>([])
  const sideEffects   = ref<Effect[]>([])
  const trendData     = ref<TrendPoint[]>([])
  const signalEvents  = ref<object[]>([])
  const reviewClusters = ref<ReviewCluster[]>([])

  const effectFilter  = ref<EffectFilter>('sideeffects')
  const viewMode      = ref<ViewMode>('neutral')    // v4.3 default: neutral overview
  const hoveredPart   = ref<string | null>(null)
  const currentQuarter = ref<string | null>(null)

  const loading = ref({
    drug: false, overview: false, benefits: false, sideEffects: false,
    trend: false, reviews: false,
  })
  const errors = ref({
    drug: '', overview: '', benefits: '', sideEffects: '', trend: '', reviews: '',
  })
  const warnings = ref({
    drug: [] as string[], overview: [] as string[],
    benefits: [] as string[], sideEffects: [] as string[],
    trend: [] as string[], reviews: [] as string[],
  })

  // ── Computed ───────────────────────────────────────────────────────────
  const filteredEffects = computed<Effect[]>(() => {
    const all = [...benefits.value, ...sideEffects.value]
    switch (effectFilter.value) {
      case 'benefits':   return benefits.value
      case 'sideeffects': return sideEffects.value
      case 'high':       return all.filter(e => e.severity === 'high')
      default:           return all
    }
  })

  // AnatomyBody reads this directly: determines which effects to render based on viewMode
  const anatomyEffects = computed<Effect[]>(() => {
    switch (viewMode.value) {
      case 'benefits':     return benefits.value
      case 'side_effects': return sideEffects.value
      case 'both':
      case 'neutral':      return [...benefits.value, ...sideEffects.value]
    }
  })

  const currentTrendFrame = computed<TrendPoint[]>(() => {
    if (!currentQuarter.value) return []
    return trendData.value.filter(p => p.quarter === currentQuarter.value)
  })

  // ── Actions ────────────────────────────────────────────────────────────
  async function loadDrug(id: number) {
    currentDrug.value = null
    overview.value = null
    benefits.value = []
    sideEffects.value = []
    trendData.value = []
    reviewClusters.value = []
    errors.value = { drug: '', overview: '', benefits: '', sideEffects: '', trend: '', reviews: '' }

    loading.value.drug = true
    try {
      const res = await api.getDrug(id)
      currentDrug.value = res.data.data
      warnings.value.drug = res.data.warnings
    } catch {
      errors.value.drug = 'Failed to load drug summary.'
    } finally {
      loading.value.drug = false
    }
  }

  async function loadOverview(id: number) {
    loading.value.overview = true
    try {
      const res = await api.getOverview(id)
      overview.value = res.data.data
      warnings.value.overview = res.data.warnings
    } catch {
      errors.value.overview = 'Overview not available.'
    } finally {
      loading.value.overview = false
    }
  }

  async function loadEffects(id: number) {
    loading.value.benefits = true
    loading.value.sideEffects = true
    try {
      const [bRes, seRes] = await Promise.allSettled([
        api.getBenefits(id),
        api.getSideEffects(id),
      ])
      if (bRes.status === 'fulfilled') {
        benefits.value = bRes.value.data.data || []
        warnings.value.benefits = bRes.value.data.warnings
      } else {
        errors.value.benefits = 'Benefits data unavailable.'
      }
      if (seRes.status === 'fulfilled') {
        sideEffects.value = seRes.value.data.data || []
        warnings.value.sideEffects = seRes.value.data.warnings
      } else {
        errors.value.sideEffects = 'Side effect data unavailable.'
      }
    } finally {
      loading.value.benefits = false
      loading.value.sideEffects = false
    }
  }

  async function loadTrend(id: number) {
    loading.value.trend = true
    try {
      const res = await api.getTrend(id)
      trendData.value = res.data.data.timeline || []
      signalEvents.value = res.data.data.signal_events || []
      warnings.value.trend = res.data.warnings
      // Default to the most recent quarter
      const quarters = [...new Set(trendData.value.map(p => p.quarter))].sort()
      currentQuarter.value = quarters.at(-1) ?? null
    } catch {
      errors.value.trend = 'Timeline data unavailable.'
    } finally {
      loading.value.trend = false
    }
  }

  async function loadReviews(id: number) {
    loading.value.reviews = true
    try {
      const res = await api.getReviews(id)
      reviewClusters.value = res.data.data.clusters || []
      warnings.value.reviews = res.data.warnings
    } catch {
      errors.value.reviews = 'Patient review data unavailable.'
    } finally {
      loading.value.reviews = false
    }
  }

  return {
    currentDrug, overview, benefits, sideEffects, trendData, signalEvents, reviewClusters,
    effectFilter, viewMode, hoveredPart, currentQuarter,
    loading, errors, warnings,
    filteredEffects, anatomyEffects, currentTrendFrame,
    loadDrug, loadOverview, loadEffects, loadTrend, loadReviews,
  }
})
