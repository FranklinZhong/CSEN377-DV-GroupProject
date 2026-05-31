/**
 * Spiral packing of words into a rectangular zone, with AABB collision
 * detection between previously placed words.
 *
 * Used by CorpusWordCloud to lay out each organ's top-N TF-IDF terms into a
 * pre-defined per-organ rectangle. Smaller / lower-scoring words spiral
 * outward from the rectangle's centroid until they find an unoccupied slot
 * inside the zone (with a small soft-overflow margin). Words that can't be
 * placed after `maxSpiralSteps` iterations are silently dropped.
 */

export interface InputWord {
  term: string
  score_norm: number
  rank: number
}

export interface PlacedWord {
  term: string
  x: number          // text center (SVG coords)
  y: number
  fontSize: number   // px (within SVG viewBox units)
  opacity: number    // 0–1
  width: number      // measured render width
  height: number     // ~fontSize * 1.15
  rank: number
  score_norm: number
}

export interface Zone {
  x: number; y: number; w: number; h: number
}

export interface PlaceOptions {
  maxWords: number
  minFontSize: number
  maxFontSize: number
  fontFamily?: string
  fontWeight?: number | string
  padding?: number     // gap between adjacent words (default 1.5)
  overflow?: number    // softness of zone boundary in px (default 4)
  maxSpiralSteps?: number  // default 700
}

export function placeWordsInBBox(
  zone: Zone,
  words: InputWord[],
  options: PlaceOptions,
): PlacedWord[] {
  const padding   = options.padding   ?? 1.5
  const overflow  = options.overflow  ?? 4
  const maxSteps  = options.maxSpiralSteps ?? 700
  const family    = options.fontFamily ?? 'Playfair Display, Georgia, serif'
  const weight    = options.fontWeight ?? 600

  const sorted = [...words]
    .sort((a, b) => b.score_norm - a.score_norm)
    .slice(0, options.maxWords)

  const cx = zone.x + zone.w / 2
  const cy = zone.y + zone.h / 2
  const xmin = zone.x - overflow
  const xmax = zone.x + zone.w + overflow
  const ymin = zone.y - overflow
  const ymax = zone.y + zone.h + overflow

  const placed: PlacedWord[] = []

  for (const w of sorted) {
    const fs = options.minFontSize +
      w.score_norm * (options.maxFontSize - options.minFontSize)
    const { width, height } = measureText(w.term, fs, family, weight)

    // First word: try exact center.
    if (placed.length === 0 && fitsInZone(cx, cy, width, height, xmin, xmax, ymin, ymax)) {
      placed.push(makePlaced(w, cx, cy, fs, width, height))
      continue
    }

    let positioned = false
    let theta = 0
    for (let step = 1; step <= maxSteps; step++) {
      theta += 0.22 + step * 0.0007
      const r = 0.55 * step
      const px = cx + r * Math.cos(theta)
      const py = cy + r * Math.sin(theta)

      if (!fitsInZone(px, py, width, height, xmin, xmax, ymin, ymax)) continue
      if (collidesAny(px, py, width, height, placed, padding))   continue

      placed.push(makePlaced(w, px, py, fs, width, height))
      positioned = true
      break
    }

    // Final fallback for the very first word in a tight zone — accept
    // any non-colliding position even at zone edge.
    if (!positioned && placed.length === 0) {
      placed.push(makePlaced(w, cx, cy, fs, width, height))
    }
  }

  return placed
}

function makePlaced(
  w: InputWord, x: number, y: number, fs: number, width: number, height: number,
): PlacedWord {
  return {
    term: w.term,
    x, y,
    fontSize: fs,
    opacity: 0.55 + w.score_norm * 0.45,  // 0.55–1.0
    width, height,
    rank: w.rank,
    score_norm: w.score_norm,
  }
}

function fitsInZone(
  cx: number, cy: number, w: number, h: number,
  xmin: number, xmax: number, ymin: number, ymax: number,
): boolean {
  return (cx - w / 2 >= xmin) && (cx + w / 2 <= xmax)
      && (cy - h / 2 >= ymin) && (cy + h / 2 <= ymax)
}

function collidesAny(
  cx: number, cy: number, w: number, h: number,
  placed: PlacedWord[], padding: number,
): boolean {
  const x1 = cx - w / 2 - padding
  const x2 = cx + w / 2 + padding
  const y1 = cy - h / 2 - padding
  const y2 = cy + h / 2 + padding
  for (const p of placed) {
    const px1 = p.x - p.width  / 2
    const px2 = p.x + p.width  / 2
    const py1 = p.y - p.height / 2
    const py2 = p.y + p.height / 2
    if (x1 < px2 && x2 > px1 && y1 < py2 && y2 > py1) return true
  }
  return false
}

// ── Text measurement (browser canvas; falls back to a heuristic in jsdom) ──

let _measureCanvas: HTMLCanvasElement | null = null

function measureText(
  text: string, fontSize: number, family: string, weight: number | string,
): { width: number; height: number } {
  try {
    if (typeof document !== 'undefined') {
      if (!_measureCanvas) _measureCanvas = document.createElement('canvas')
      const ctx = _measureCanvas.getContext('2d')
      if (ctx) {
        ctx.font = `${weight} ${fontSize}px ${family}`
        const m = ctx.measureText(text)
        if (m.width > 0) return { width: m.width, height: fontSize * 1.15 }
      }
    }
  } catch { /* fall through to heuristic */ }
  // Heuristic — used in test envs (jsdom canvas returns width=0 or null ctx)
  return { width: text.length * fontSize * 0.55, height: fontSize * 1.15 }
}
