import axios from 'axios'

const client = axios.create({
  baseURL: '',   // Vite proxy forwards /api/* → localhost:8000, no CORS needed
  timeout: 30000,
})

// ── Types (mirrors backend/schemas/common.py) ─────────────────────────────

export interface Meta {
  source: string
  data_version: string
  confidence: 'high' | 'medium' | 'low' | 'insufficient'
  report_count: number | null
}

export interface ApiResponse<T> {
  success: boolean
  data: T
  meta: Meta
  warnings: string[]
}

export interface ApiError {
  success: false
  error: { code: string; message: string }
  suggestions: string[]
}

// ── Drug types ────────────────────────────────────────────────────────────

export interface DrugResult {
  drug_id: number
  name: string
  generic_name: string | null
  main_use: string | null
  risk_level: string
  review_count: number
  data_quality: 'full' | 'partial' | 'limited'
  match_type: string
  score: number
}

export interface DrugSummary {
  drug_id: number
  name: string
  generic_name: string | null
  brand_name: string | null
  main_use: string | null
  overall_rating: number | null
  risk_level: string
  also_known_as: string[]
  data_sources: string[]
  data_version: string
  updated_at: string | null
  data_coverage?: {
    benefits: number
    side_effects: number
    reviews: number
    trend_quarters: number
  }
}

export interface DrugOverview {
  what_it_treats: string | null
  how_it_works:   string | null
  quick_facts: {
    dosage_form: string | null
    route:       string | null
    rating:      number | null
    risk_level:  string | null
  }
  key_indications: string[]
}

export interface Effect {
  body_part: string
  svg_region: string
  effect_name: string
  effect_type: 'benefit' | 'side_effect'
  severity: 'low' | 'medium' | 'high' | 'unknown'
  source: string
  frequency: number | null
  confidence: string
  description: string | null
}

export interface TrendPoint {
  quarter: string
  body_part: string
  svg_region: string
  report_count: number
  normalized_frequency: number
  signal_flag: boolean
  missing: boolean
  confidence: string
}

export interface ReviewCluster {
  body_part: string
  sentiment: 'positive' | 'negative' | 'mixed' | 'neutral'
  review_count: number
  top_terms: string[]
  representative_quotes: string[]
}

export interface ReviewRow {
  id: number
  rating: number | null
  sentiment: 'positive' | 'negative' | 'mixed' | 'neutral'
  review_text: string
  body_parts: string[]
  source: string
}

export interface ReviewListResponse {
  total: number
  page: number
  page_size: number
  total_pages: number
  reviews: ReviewRow[]
}

export type ReviewSort = 'recent' | 'rating_desc' | 'rating_asc'

export interface ReviewListQuery {
  body_part?: string          // 'all' or specific
  sentiment?: string          // 'all' or specific
  rating_min?: number
  rating_max?: number
  q?: string
  sort?: ReviewSort
  page?: number
  page_size?: number
}

// ── API functions ─────────────────────────────────────────────────────────

export const api = {
  // Search
  search: (q: string) =>
    client.get<ApiResponse<DrugResult[]>>('/api/search', { params: { q } }),

  searchFuzzy: (q: string) =>
    client.get<ApiResponse<{ exact_match: null; suggestions: DrugResult[]; auto_redirect: boolean }>>(
      '/api/search/fuzzy', { params: { q } }
    ),

  searchIndex: (letter: string, prefix?: string) =>
    client.get<ApiResponse<{ results: DrugResult[] }>>('/api/search/index', {
      params: { letter, ...(prefix && { prefix }) },
    }),

  searchByBodyPart: (part: string) =>
    client.get<ApiResponse<{ part: string; results: DrugResult[]; empty: boolean }>>(
      '/api/search/by-body-part', { params: { part } }
    ),

  // Drug details
  getDrug: (id: number) =>
    client.get<ApiResponse<DrugSummary>>(`/api/drugs/${id}`),

  getOverview: (id: number) =>
    client.get<ApiResponse<DrugOverview>>(`/api/drugs/${id}/overview`),

  getBenefits: (id: number) =>
    client.get<ApiResponse<Effect[]>>(`/api/drugs/${id}/benefits`),

  getSideEffects: (id: number) =>
    client.get<ApiResponse<Effect[]>>(`/api/drugs/${id}/sideeffects`),

  getTrend: (id: number) =>
    client.get<ApiResponse<{ drug_id: number; drug_name: string; timeline: TrendPoint[]; signal_events: object[] }>>(
      `/api/drugs/${id}/trend`
    ),

  getReviews: (id: number) =>
    client.get<ApiResponse<{ clusters: ReviewCluster[] }>>(`/api/drugs/${id}/reviews`),

  getReviewsList: (id: number, params: ReviewListQuery = {}) =>
    client.get<ApiResponse<ReviewListResponse>>(
      `/api/drugs/${id}/reviews/list`, { params },
    ),

  // Corpus-level NLP analytics
  getCorpusNlp: () =>
    client.get<ApiResponse<{
      tfidf: Record<string, { term: string; score_norm: number; rank: number }[]>
      sentiment: {
        body_part: string
        positive: number; negative: number; neutral: number; total: number
        positive_pct: number; negative_pct: number; neutral_pct: number
      }[]
    }>>('/api/corpus/nlp'),

  // Health check
  health: () => client.get('/api/health'),
}

export default client
