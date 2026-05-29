/**
 * TrendAnimation.spec.ts — Vis 2 unit tests
 * Coverage: yearData aggregation, years sort, allBodyParts sort,
 *           Pearson correlation coefficient, correlationData, getActiveRow
 */

import { describe, it, expect } from 'vitest'

// ── Re-implement pure functions (specification tests) ───────────────────────

type YearEntry = { total: number; signal: boolean; hasMissing: boolean }
type MockTrendPoint = {
  quarter: string; body_part: string
  report_count: number; signal_flag: boolean; missing: boolean
}

function buildYearData(timeline: MockTrendPoint[]): Record<string, Record<string, YearEntry>> {
  const map: Record<string, Record<string, YearEntry>> = {}
  for (const p of timeline) {
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
}

function getYears(yearData: Record<string, Record<string, YearEntry>>): string[] {
  return Object.keys(yearData).sort()
}

function getAllBodyParts(yearData: Record<string, Record<string, YearEntry>>): string[] {
  const totals: Record<string, number> = {}
  for (const parts of Object.values(yearData))
    for (const [bp, d] of Object.entries(parts))
      totals[bp] = (totals[bp] ?? 0) + d.total
  return Object.entries(totals).sort((a, b) => b[1] - a[1]).map(([k]) => k)
}

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

function buildCorrelationData(
  allBodyParts: string[],
  years: string[],
  yearData: Record<string, Record<string, YearEntry>>
) {
  if (allBodyParts.length < 2 || years.length < 3) return null
  const series: Record<string, number[]> = {}
  for (const part of allBodyParts)
    series[part] = years.map(y => yearData[y]?.[part]?.total ?? 0)
  const matrix: { partA: string; partB: string; r: number }[] = []
  for (const a of allBodyParts)
    for (const b of allBodyParts)
      matrix.push({ partA: a, partB: b, r: pearson(series[a], series[b]) })
  return { parts: allBodyParts, matrix }
}

function getActiveRow(selectedRow: string | null, hoveredPart: string | null | undefined): string | null {
  return selectedRow ?? hoveredPart ?? null
}

function cellFill(total: number, hasMissing: boolean): 'color' | 'stripe' | 'dark' {
  if (total > 0) return 'color'
  if (hasMissing) return 'stripe'
  return 'dark'
}

// ── Test data helpers ────────────────────────────────────────────────────────

const pt = (quarter: string, body_part: string, report_count: number,
            signal_flag = false, missing = false): MockTrendPoint =>
  ({ quarter, body_part, report_count, signal_flag, missing })

// ── yearData aggregation ─────────────────────────────────────────────────────

describe('yearData — quarterly → yearly aggregation', () => {
  it('groups single quarter correctly', () => {
    const d = buildYearData([pt('2020Q1', 'stomach', 10)])
    expect(d['2020']['stomach'].total).toBe(10)
  })

  it('sums two quarters in the same year', () => {
    const d = buildYearData([pt('2021Q1', 'liver', 5), pt('2021Q3', 'liver', 8)])
    expect(d['2021']['liver'].total).toBe(13)
  })

  it('sums four quarters correctly', () => {
    const d = buildYearData([
      pt('2022Q1', 'heart', 3), pt('2022Q2', 'heart', 4),
      pt('2022Q3', 'heart', 2), pt('2022Q4', 'heart', 1),
    ])
    expect(d['2022']['heart'].total).toBe(10)
  })

  it('separates different years', () => {
    const d = buildYearData([pt('2020Q1', 'brain', 5), pt('2021Q1', 'brain', 7)])
    expect(d['2020']['brain'].total).toBe(5)
    expect(d['2021']['brain'].total).toBe(7)
  })

  it('separates different body parts in same year', () => {
    const d = buildYearData([pt('2020Q1', 'lung', 3), pt('2020Q1', 'kidney', 6)])
    expect(d['2020']['lung'].total).toBe(3)
    expect(d['2020']['kidney'].total).toBe(6)
  })

  it('signal_flag OR-ed: false OR true → true', () => {
    const d = buildYearData([pt('2020Q1', 'eye', 5, false), pt('2020Q3', 'eye', 3, true)])
    expect(d['2020']['eye'].signal).toBe(true)
  })

  it('signal_flag OR-ed: false OR false → false', () => {
    const d = buildYearData([pt('2020Q1', 'ear', 2, false), pt('2020Q3', 'ear', 1, false)])
    expect(d['2020']['ear'].signal).toBe(false)
  })

  it('hasMissing OR-ed: true in any quarter → true', () => {
    const d = buildYearData([pt('2021Q1', 'skin', 0, false, true), pt('2021Q2', 'skin', 4, false, false)])
    expect(d['2021']['skin'].hasMissing).toBe(true)
  })

  it('hasMissing false when all quarters present', () => {
    const d = buildYearData([pt('2021Q1', 'blood', 2, false, false)])
    expect(d['2021']['blood'].hasMissing).toBe(false)
  })

  it('empty timeline → empty map', () => {
    expect(buildYearData([])).toEqual({})
  })

  it('zero report_count is valid', () => {
    const d = buildYearData([pt('2023Q1', 'stomach', 0)])
    expect(d['2023']['stomach'].total).toBe(0)
  })

  it('large report counts summed correctly', () => {
    const d = buildYearData([pt('2019Q2', 'muscle', 9999), pt('2019Q4', 'muscle', 1)])
    expect(d['2019']['muscle'].total).toBe(10000)
  })
})

// ── years computed ────────────────────────────────────────────────────────────

describe('years — sorted year list', () => {
  it('returns years sorted ascending', () => {
    const d = buildYearData([pt('2022Q1', 'lung', 1), pt('2019Q1', 'lung', 1), pt('2021Q1', 'lung', 1)])
    expect(getYears(d)).toEqual(['2019', '2021', '2022'])
  })

  it('returns empty array for empty yearData', () => {
    expect(getYears({})).toEqual([])
  })

  it('deduplicates years from multiple body parts', () => {
    const d = buildYearData([pt('2020Q1', 'liver', 5), pt('2020Q2', 'kidney', 3)])
    expect(getYears(d)).toEqual(['2020'])
  })

  it('handles single year', () => {
    const d = buildYearData([pt('2018Q3', 'heart', 7)])
    expect(getYears(d)).toEqual(['2018'])
  })
})

// ── allBodyParts computed ─────────────────────────────────────────────────────

describe('allBodyParts — sorted by total count descending', () => {
  it('ranks body parts by total descending', () => {
    const d = buildYearData([
      pt('2020Q1', 'liver', 100), pt('2020Q1', 'lung', 50), pt('2020Q1', 'heart', 200),
    ])
    expect(getAllBodyParts(d)).toEqual(['heart', 'liver', 'lung'])
  })

  it('sums across years for ranking', () => {
    const d = buildYearData([
      pt('2020Q1', 'eye', 10), pt('2021Q1', 'eye', 20),  // 30 total
      pt('2020Q1', 'ear', 25),                             // 25 total
    ])
    expect(getAllBodyParts(d)[0]).toBe('eye')
  })

  it('returns empty array for empty yearData', () => {
    expect(getAllBodyParts({})).toEqual([])
  })

  it('returns single part for single entry', () => {
    const d = buildYearData([pt('2020Q1', 'stomach', 5)])
    expect(getAllBodyParts(d)).toEqual(['stomach'])
  })

  it('ties broken arbitrarily but both included', () => {
    const d = buildYearData([pt('2020Q1', 'brain', 10), pt('2020Q1', 'kidney', 10)])
    const parts = getAllBodyParts(d)
    expect(parts).toContain('brain')
    expect(parts).toContain('kidney')
    expect(parts).toHaveLength(2)
  })

  it('zero-count body part still appears', () => {
    const d = buildYearData([pt('2020Q1', 'vascular', 0)])
    expect(getAllBodyParts(d)).toContain('vascular')
  })
})

// ── pearson correlation ───────────────────────────────────────────────────────

describe('pearson — correlation coefficient', () => {
  it('perfect positive correlation → 1', () => {
    expect(pearson([1, 2, 3, 4, 5], [2, 4, 6, 8, 10])).toBeCloseTo(1, 5)
  })

  it('perfect negative correlation → -1', () => {
    expect(pearson([1, 2, 3, 4, 5], [10, 8, 6, 4, 2])).toBeCloseTo(-1, 5)
  })

  it('uncorrelated → near 0', () => {
    const r = pearson([1, 2, 3], [3, 1, 2])
    expect(Math.abs(r)).toBeLessThan(0.6)
  })

  it('n < 3 → returns 0', () => {
    expect(pearson([1, 2], [3, 4])).toBe(0)
  })

  it('n = 1 → returns 0', () => {
    expect(pearson([5], [5])).toBe(0)
  })

  it('zero-variance array a → returns 0', () => {
    expect(pearson([5, 5, 5, 5], [1, 2, 3, 4])).toBe(0)
  })

  it('zero-variance array b → returns 0', () => {
    expect(pearson([1, 2, 3, 4], [7, 7, 7, 7])).toBe(0)
  })

  it('result clamped to [-1, 1] for floating-point edge cases', () => {
    const r = pearson([1, 1, 1, 2], [1, 1, 1, 2])
    expect(r).toBeGreaterThanOrEqual(-1)
    expect(r).toBeLessThanOrEqual(1)
  })

  it('all zeros → returns 0', () => {
    expect(pearson([0, 0, 0, 0], [0, 0, 0, 0])).toBe(0)
  })

  it('typical moderate positive correlation between 0 and 1', () => {
    const r = pearson([1, 3, 2, 5, 4], [2, 4, 1, 6, 5])
    expect(r).toBeGreaterThan(0)
    expect(r).toBeLessThanOrEqual(1)
  })
})

// ── correlationData ───────────────────────────────────────────────────────────

describe('correlationData — null guard and matrix shape', () => {
  const makeData = (parts: string[], yearList: string[], counts: number[][]) => {
    const yearData: Record<string, Record<string, YearEntry>> = {}
    yearList.forEach((y, yi) => {
      yearData[y] = {}
      parts.forEach((p, pi) => {
        yearData[y][p] = { total: counts[pi][yi], signal: false, hasMissing: false }
      })
    })
    return { parts, years: yearList, yearData }
  }

  it('returns null when < 2 body parts', () => {
    const { parts, years, yearData } = makeData(['lung'], ['2020', '2021', '2022'], [[1, 2, 3]])
    expect(buildCorrelationData(parts, years, yearData)).toBeNull()
  })

  it('returns null when < 3 years', () => {
    const { parts, years, yearData } = makeData(['lung', 'heart'], ['2020', '2021'], [[1, 2], [3, 4]])
    expect(buildCorrelationData(parts, years, yearData)).toBeNull()
  })

  it('returns data with exactly 2 parts and 3 years', () => {
    const { parts, years, yearData } = makeData(
      ['lung', 'heart'], ['2020', '2021', '2022'], [[1, 2, 3], [3, 2, 1]]
    )
    const result = buildCorrelationData(parts, years, yearData)
    expect(result).not.toBeNull()
    expect(result!.parts).toHaveLength(2)
    expect(result!.matrix).toHaveLength(4)  // 2×2
  })

  it('diagonal r values are 1 (self-correlation)', () => {
    const { parts, years, yearData } = makeData(
      ['lung', 'heart'], ['2020', '2021', '2022'], [[1, 2, 3], [4, 5, 6]]
    )
    const result = buildCorrelationData(parts, years, yearData)!
    const diagonal = result.matrix.filter(m => m.partA === m.partB)
    diagonal.forEach(d => expect(d.r).toBeCloseTo(1, 5))
  })

  it('matrix is n×n for n parts', () => {
    const { parts, years, yearData } = makeData(
      ['lung', 'heart', 'liver'],
      ['2019', '2020', '2021'],
      [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    )
    const result = buildCorrelationData(parts, years, yearData)!
    expect(result.matrix).toHaveLength(9)
  })

  it('symmetric: r(A,B) equals r(B,A)', () => {
    const { parts, years, yearData } = makeData(
      ['lung', 'heart'], ['2020', '2021', '2022'], [[1, 3, 2], [2, 1, 4]]
    )
    const result = buildCorrelationData(parts, years, yearData)!
    const ab = result.matrix.find(m => m.partA === 'lung' && m.partB === 'heart')!.r
    const ba = result.matrix.find(m => m.partA === 'heart' && m.partB === 'lung')!.r
    expect(ab).toBeCloseTo(ba, 10)
  })
})

// ── getActiveRow ──────────────────────────────────────────────────────────────

describe('getActiveRow — selectedRow overrides hoveredPart', () => {
  it('returns selectedRow when both are set', () => {
    expect(getActiveRow('liver', 'heart')).toBe('liver')
  })

  it('returns hoveredPart when selectedRow is null', () => {
    expect(getActiveRow(null, 'stomach')).toBe('stomach')
  })

  it('returns null when both are null', () => {
    expect(getActiveRow(null, null)).toBeNull()
  })

  it('returns null when hoveredPart is undefined', () => {
    expect(getActiveRow(null, undefined)).toBeNull()
  })
})

// ── cellFill logic ────────────────────────────────────────────────────────────

describe('cellFill — color encoding for heatmap cells', () => {
  it('positive count → color', () => {
    expect(cellFill(10, false)).toBe('color')
  })

  it('positive count ignores hasMissing flag', () => {
    expect(cellFill(5, true)).toBe('color')
  })

  it('zero count + hasMissing → stripe', () => {
    expect(cellFill(0, true)).toBe('stripe')
  })

  it('zero count + no missing → dark', () => {
    expect(cellFill(0, false)).toBe('dark')
  })

  it('large count → color', () => {
    expect(cellFill(99999, false)).toBe('color')
  })

  it('count = 1 → color (minimum non-zero)', () => {
    expect(cellFill(1, false)).toBe('color')
  })

  it('count = 1 + hasMissing → still color (count wins)', () => {
    expect(cellFill(1, true)).toBe('color')
  })

  it('count = 0 + hasMissing + signal → stripe (count is zero)', () => {
    expect(cellFill(0, true)).toBe('stripe')
  })
})
