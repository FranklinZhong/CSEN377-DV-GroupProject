/**
 * wordCloudLayout.spec.ts — placement algorithm contracts
 *
 * The spiral packer should:
 *  1. Honor maxWords and order by score_norm desc
 *  2. Scale font size from minFontSize..maxFontSize by score_norm
 *  3. Keep every placed word inside the zone (with overflow tolerance)
 *  4. Never overlap two placed words (with padding)
 *  5. Gracefully drop words that won't fit instead of forcing them
 */

import { describe, it, expect } from 'vitest'
import {
  placeWordsInBBox,
  type InputWord,
  type PlacedWord,
} from '@/utils/wordCloudLayout'

const makeWords = (n: number): InputWord[] =>
  Array.from({ length: n }, (_, i) => ({
    term: `term${i}`,
    score_norm: 1 - i * (1 / n),
    rank: i + 1,
  }))

function aabbOverlaps(a: PlacedWord, b: PlacedWord, padding = 0): boolean {
  const ax1 = a.x - a.width  / 2 - padding
  const ax2 = a.x + a.width  / 2 + padding
  const ay1 = a.y - a.height / 2 - padding
  const ay2 = a.y + a.height / 2 + padding
  const bx1 = b.x - b.width  / 2
  const bx2 = b.x + b.width  / 2
  const by1 = b.y - b.height / 2
  const by2 = b.y + b.height / 2
  return ax1 < bx2 && ax2 > bx1 && ay1 < by2 && ay2 > by1
}

describe('placeWordsInBBox', () => {
  const zone = { x: 100, y: 100, w: 200, h: 200 }

  it('respects maxWords cap', () => {
    const placed = placeWordsInBBox(zone, makeWords(20), {
      maxWords: 5, minFontSize: 8, maxFontSize: 18,
    })
    expect(placed.length).toBeLessThanOrEqual(5)
  })

  it('returns words sorted by score_norm desc (largest first)', () => {
    const placed = placeWordsInBBox(zone, makeWords(8), {
      maxWords: 8, minFontSize: 8, maxFontSize: 24,
    })
    for (let i = 1; i < placed.length; i++) {
      expect(placed[i - 1].score_norm).toBeGreaterThanOrEqual(placed[i].score_norm)
    }
  })

  it('scales font size between min and max by score_norm', () => {
    const placed = placeWordsInBBox(zone, makeWords(4), {
      maxWords: 4, minFontSize: 10, maxFontSize: 22,
    })
    for (const p of placed) {
      expect(p.fontSize).toBeGreaterThanOrEqual(10)
      expect(p.fontSize).toBeLessThanOrEqual(22)
    }
    // Top-ranked word (score_norm closest to 1) has the largest font
    expect(placed[0].fontSize).toBeGreaterThan(placed[placed.length - 1].fontSize)
  })

  it('all placed words stay within zone + overflow tolerance', () => {
    const placed = placeWordsInBBox(zone, makeWords(6), {
      maxWords: 6, minFontSize: 10, maxFontSize: 18, overflow: 6,
    })
    for (const p of placed) {
      expect(p.x - p.width  / 2).toBeGreaterThanOrEqual(zone.x - 6 - 0.001)
      expect(p.x + p.width  / 2).toBeLessThanOrEqual(zone.x + zone.w + 6 + 0.001)
      expect(p.y - p.height / 2).toBeGreaterThanOrEqual(zone.y - 6 - 0.001)
      expect(p.y + p.height / 2).toBeLessThanOrEqual(zone.y + zone.h + 6 + 0.001)
    }
  })

  it('placed words do not overlap each other (within padding)', () => {
    const placed = placeWordsInBBox(zone, makeWords(6), {
      maxWords: 6, minFontSize: 10, maxFontSize: 18, padding: 1.5,
    })
    for (let i = 0; i < placed.length; i++) {
      for (let j = i + 1; j < placed.length; j++) {
        // The packer guards collisions with a positive padding; verify that
        // raw AABBs don't overlap.
        expect(aabbOverlaps(placed[i], placed[j], 0)).toBe(false)
      }
    }
  })

  it('drops words that cannot fit in a tight zone (no force-placement of extras)', () => {
    const tiny = { x: 0, y: 0, w: 18, h: 12 }
    const placed = placeWordsInBBox(tiny, makeWords(10), {
      maxWords: 10, minFontSize: 12, maxFontSize: 28,
    })
    // The first word is placed at center as a guaranteed fallback; subsequent
    // ones must squeeze in. We expect far fewer than 10.
    expect(placed.length).toBeLessThan(10)
  })

  it('opacity correlates with score_norm', () => {
    const placed = placeWordsInBBox(zone, makeWords(5), {
      maxWords: 5, minFontSize: 10, maxFontSize: 18,
    })
    for (const p of placed) {
      expect(p.opacity).toBeGreaterThanOrEqual(0.55)
      expect(p.opacity).toBeLessThanOrEqual(1.0)
    }
    // Higher score → higher opacity
    expect(placed[0].opacity).toBeGreaterThanOrEqual(placed[placed.length - 1].opacity)
  })

  it('handles empty input', () => {
    const placed = placeWordsInBBox(zone, [], {
      maxWords: 5, minFontSize: 8, maxFontSize: 16,
    })
    expect(placed).toEqual([])
  })

  it('preserves rank metadata on placed words', () => {
    const placed = placeWordsInBBox(zone, makeWords(3), {
      maxWords: 3, minFontSize: 10, maxFontSize: 18,
    })
    for (const p of placed) {
      expect(p.rank).toBeGreaterThan(0)
      expect(p.term).toBeTruthy()
    }
  })
})
