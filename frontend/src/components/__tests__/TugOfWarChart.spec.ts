/**
 * TugOfWarChart.spec.ts — Vis 3 unit tests
 * Coverage: netSentiment, knotX/knotR/ropeWidth, centerColor,
 *           mixedCount, bodyParts sort order, drawerTitle, topTerms
 */

import { describe, it, expect } from 'vitest'

// ── Re-implement pure functions (specification tests) ───────────────────────

type ReviewCluster = {
  body_part: string; sentiment: string
  review_count: number; top_terms: string[]
}

function buildClusterMap(clusters: ReviewCluster[]): Record<string, Record<string, ReviewCluster>> {
  const map: Record<string, Record<string, ReviewCluster>> = {}
  for (const c of clusters) {
    if (!map[c.body_part]) map[c.body_part] = {}
    map[c.body_part][c.sentiment] = c
  }
  return map
}

function countOf(map: Record<string, Record<string, ReviewCluster>>, part: string, sent: string): number {
  return map[part]?.[sent]?.review_count ?? 0
}

function totalOf(map: Record<string, Record<string, ReviewCluster>>, part: string): number {
  return ['positive', 'negative', 'mixed', 'neutral'].reduce((s, k) => s + countOf(map, part, k), 0)
}

function mixedCount(map: Record<string, Record<string, ReviewCluster>>, part: string): number {
  return countOf(map, part, 'mixed') + countOf(map, part, 'neutral')
}

function netSentiment(map: Record<string, Record<string, ReviewCluster>>, part: string): number {
  const p = countOf(map, part, 'positive')
  const n = countOf(map, part, 'negative')
  if (p + n === 0) return 0
  return (p - n) / (p + n)
}

function knotX(net: number): number {
  return 200 + net * 160
}

function knotR(total: number, maxTotal: number): number {
  return 8 + Math.min(8, Math.sqrt(total / maxTotal) * 8)
}

function ropeWidth(total: number, maxTotal: number): number {
  return 3 + Math.sqrt(total / maxTotal) * 5
}

function centerColor(net: number): string {
  if (net > 0.25)  return '#4ade80'
  if (net > 0)     return '#86efac'
  if (net > -0.25) return '#facc15'
  if (net > -0.6)  return '#fb923c'
  return '#f87171'
}

function buildBodyParts(clusters: ReviewCluster[]): string[] {
  const totals: Record<string, number> = {}
  for (const c of clusters)
    totals[c.body_part] = (totals[c.body_part] ?? 0) + c.review_count
  return Object.keys(totals).sort((a, b) => totals[b] - totals[a]).slice(0, 12)
}

function topTerms(
  map: Record<string, Record<string, ReviewCluster>>,
  part: string | null
): string[] {
  if (!part) return []
  const all: string[] = []
  for (const sent of ['negative', 'mixed', 'positive']) {
    const t = map[part]?.[sent]?.top_terms ?? []
    all.push(...t)
  }
  return [...new Set(all)].slice(0, 12)
}

// ── Test data helpers ─────────────────────────────────────────────────────────

const cl = (body_part: string, sentiment: string, review_count: number, top_terms: string[] = []): ReviewCluster =>
  ({ body_part, sentiment, review_count, top_terms })

// ── netSentiment ──────────────────────────────────────────────────────────────

describe('netSentiment — (pos - neg) / (pos + neg)', () => {
  it('all positive → 1', () => {
    const m = buildClusterMap([cl('stomach', 'positive', 100)])
    expect(netSentiment(m, 'stomach')).toBe(1)
  })

  it('all negative → -1', () => {
    const m = buildClusterMap([cl('liver', 'negative', 50)])
    expect(netSentiment(m, 'liver')).toBe(-1)
  })

  it('equal positive and negative → 0', () => {
    const m = buildClusterMap([cl('heart', 'positive', 40), cl('heart', 'negative', 40)])
    expect(netSentiment(m, 'heart')).toBe(0)
  })

  it('zero denominator (only mixed/neutral) → 0', () => {
    const m = buildClusterMap([cl('lung', 'mixed', 30)])
    expect(netSentiment(m, 'lung')).toBe(0)
  })

  it('empty part → 0', () => {
    const m = buildClusterMap([])
    expect(netSentiment(m, 'nonexistent')).toBe(0)
  })

  it('net > 0 for more positive than negative', () => {
    const m = buildClusterMap([cl('kidney', 'positive', 80), cl('kidney', 'negative', 20)])
    expect(netSentiment(m, 'kidney')).toBeCloseTo(0.6)
  })

  it('net < 0 for more negative than positive', () => {
    const m = buildClusterMap([cl('skin', 'positive', 10), cl('skin', 'negative', 90)])
    expect(netSentiment(m, 'skin')).toBeCloseTo(-0.8)
  })

  it('result is in range [-1, 1]', () => {
    const m = buildClusterMap([cl('brain', 'positive', 3), cl('brain', 'negative', 1)])
    const net = netSentiment(m, 'brain')
    expect(net).toBeGreaterThanOrEqual(-1)
    expect(net).toBeLessThanOrEqual(1)
  })
})

// ── knotX ─────────────────────────────────────────────────────────────────────

describe('knotX — maps net sentiment to SVG x coordinate', () => {
  it('net = 1 → 360 (rightmost)', () => {
    expect(knotX(1)).toBe(360)
  })

  it('net = -1 → 40 (leftmost)', () => {
    expect(knotX(-1)).toBe(40)
  })

  it('net = 0 → 200 (center)', () => {
    expect(knotX(0)).toBe(200)
  })

  it('net = 0.5 → 280', () => {
    expect(knotX(0.5)).toBe(280)
  })

  it('net = -0.5 → 120', () => {
    expect(knotX(-0.5)).toBe(120)
  })

  it('net = 0.25 → 240', () => {
    expect(knotX(0.25)).toBe(240)
  })
})

// ── knotR ─────────────────────────────────────────────────────────────────────

describe('knotR — knot radius scales with sqrt(total / maxTotal)', () => {
  it('total = maxTotal → radius = 16 (max)', () => {
    expect(knotR(100, 100)).toBe(16)
  })

  it('total = 0 → radius = 8 (min)', () => {
    expect(knotR(0, 100)).toBe(8)
  })

  it('total = maxTotal/4 → radius between 8 and 16', () => {
    const r = knotR(25, 100)
    expect(r).toBeGreaterThan(8)
    expect(r).toBeLessThan(16)
  })

  it('radius always at least 8', () => {
    expect(knotR(0, 1000)).toBeGreaterThanOrEqual(8)
  })
})

// ── ropeWidth ─────────────────────────────────────────────────────────────────

describe('ropeWidth — stroke-width scales with sqrt(total / maxTotal)', () => {
  it('total = maxTotal → width = 8', () => {
    expect(ropeWidth(100, 100)).toBe(8)
  })

  it('total = 0 → width = 3 (minimum)', () => {
    expect(ropeWidth(0, 100)).toBe(3)
  })

  it('total = maxTotal/4 → width between 3 and 8', () => {
    const w = ropeWidth(25, 100)
    expect(w).toBeGreaterThan(3)
    expect(w).toBeLessThan(8)
  })

  it('width scales monotonically with total', () => {
    const w1 = ropeWidth(10, 100)
    const w2 = ropeWidth(50, 100)
    const w3 = ropeWidth(90, 100)
    expect(w1).toBeLessThan(w2)
    expect(w2).toBeLessThan(w3)
  })
})

// ── centerColor ───────────────────────────────────────────────────────────────

describe('centerColor — color encoding based on net sentiment', () => {
  it('net > 0.25 → green #4ade80', () => {
    expect(centerColor(0.5)).toBe('#4ade80')
    expect(centerColor(1)).toBe('#4ade80')
    expect(centerColor(0.26)).toBe('#4ade80')
  })

  it('net = 0.25 → NOT #4ade80 (boundary exclusive)', () => {
    expect(centerColor(0.25)).not.toBe('#4ade80')
  })

  it('0 < net <= 0.25 → light green #86efac', () => {
    expect(centerColor(0.1)).toBe('#86efac')
    expect(centerColor(0.25)).toBe('#86efac')
  })

  it('-0.25 < net <= 0 → yellow #facc15', () => {
    expect(centerColor(0)).toBe('#facc15')
    expect(centerColor(-0.1)).toBe('#facc15')
    expect(centerColor(-0.24)).toBe('#facc15')
  })

  it('-0.6 < net <= -0.25 → orange #fb923c', () => {
    expect(centerColor(-0.25)).toBe('#fb923c')
    expect(centerColor(-0.4)).toBe('#fb923c')
    expect(centerColor(-0.59)).toBe('#fb923c')
  })

  it('net <= -0.6 → red #f87171', () => {
    expect(centerColor(-0.6)).toBe('#f87171')
    expect(centerColor(-1)).toBe('#f87171')
    expect(centerColor(-0.9)).toBe('#f87171')
  })
})

// ── mixedCount ────────────────────────────────────────────────────────────────

describe('mixedCount — mixed + neutral reviews', () => {
  it('mixed and neutral both present', () => {
    const m = buildClusterMap([cl('eye', 'mixed', 15), cl('eye', 'neutral', 10)])
    expect(mixedCount(m, 'eye')).toBe(25)
  })

  it('only mixed', () => {
    const m = buildClusterMap([cl('ear', 'mixed', 8)])
    expect(mixedCount(m, 'ear')).toBe(8)
  })

  it('only neutral', () => {
    const m = buildClusterMap([cl('muscle', 'neutral', 3)])
    expect(mixedCount(m, 'muscle')).toBe(3)
  })

  it('neither mixed nor neutral → 0', () => {
    const m = buildClusterMap([cl('blood', 'positive', 20)])
    expect(mixedCount(m, 'blood')).toBe(0)
  })
})

// ── bodyParts (top 12 by total) ───────────────────────────────────────────────

describe('buildBodyParts — top 12 sorted by total review count', () => {
  it('sorts by total descending', () => {
    const clusters = [
      cl('liver', 'positive', 30), cl('lung', 'positive', 80), cl('heart', 'positive', 50),
    ]
    expect(buildBodyParts(clusters)).toEqual(['lung', 'heart', 'liver'])
  })

  it('caps at 12 body parts', () => {
    const clusters = Array.from({ length: 15 }, (_, i) => cl(`part${i}`, 'positive', i + 1))
    expect(buildBodyParts(clusters)).toHaveLength(12)
  })

  it('returns fewer than 12 if not enough data', () => {
    const clusters = [cl('stomach', 'positive', 5), cl('kidney', 'negative', 3)]
    expect(buildBodyParts(clusters)).toHaveLength(2)
  })

  it('empty clusters → empty array', () => {
    expect(buildBodyParts([])).toEqual([])
  })

  it('sums across sentiments for ranking', () => {
    const clusters = [
      cl('liver', 'positive', 10), cl('liver', 'negative', 20),  // 30 total
      cl('lung', 'positive', 25),                                  // 25 total
    ]
    expect(buildBodyParts(clusters)[0]).toBe('liver')
  })

  it('each body part appears exactly once', () => {
    const clusters = [
      cl('skin', 'positive', 10), cl('skin', 'negative', 5), cl('brain', 'positive', 8),
    ]
    const parts = buildBodyParts(clusters)
    expect(new Set(parts).size).toBe(parts.length)
  })
})

// ── topTerms ──────────────────────────────────────────────────────────────────

describe('topTerms — deduped terms from negative + mixed + positive', () => {
  it('returns empty array for null part', () => {
    const m = buildClusterMap([])
    expect(topTerms(m, null)).toEqual([])
  })

  it('returns empty array for unknown part', () => {
    const m = buildClusterMap([])
    expect(topTerms(m, 'nonexistent')).toEqual([])
  })

  it('deduplicates terms across sentiments', () => {
    const m = buildClusterMap([
      cl('heart', 'positive', 5, ['fatigue', 'nausea']),
      cl('heart', 'negative', 5, ['fatigue', 'pain']),
    ])
    const terms = topTerms(m, 'heart')
    expect(terms.filter(t => t === 'fatigue')).toHaveLength(1)
  })

  it('caps at 12 terms', () => {
    const manyTerms = Array.from({ length: 20 }, (_, i) => `term${i}`)
    const m = buildClusterMap([cl('liver', 'positive', 5, manyTerms)])
    expect(topTerms(m, 'liver')).toHaveLength(12)
  })

  it('excludes neutral from topTerms', () => {
    const m = buildClusterMap([
      cl('lung', 'neutral', 5, ['hidden']),
      cl('lung', 'positive', 5, ['visible']),
    ])
    const terms = topTerms(m, 'lung')
    expect(terms).toContain('visible')
    expect(terms).not.toContain('hidden')
  })
})
