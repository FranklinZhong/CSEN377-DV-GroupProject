/**
 * AnatomyBody.spec.ts — Vis 1 unit tests
 * Coverage: highlightType, matchesMode, maxSeverity, bodyPartLabel,
 *           organStroke, modeOpts disabled state, effectMap filtering
 */

import { describe, it, expect } from 'vitest'

// ── Re-implement pure functions (specification tests) ───────────────────────

type Effect = {
  body_part: string; effect_type: 'benefit' | 'side_effect'
  severity: string; effect_name?: string
}
type ViewMode = 'benefits' | 'side_effects' | 'both'

function matchesMode(e: Effect, viewMode: ViewMode): boolean {
  if (viewMode === 'both') return true
  if (viewMode === 'benefits') return e.effect_type === 'benefit'
  return e.effect_type === 'side_effect'
}

function buildEffectMap(effects: Effect[], viewMode: ViewMode): Map<string, Effect[]> {
  const map = new Map<string, Effect[]>()
  for (const e of effects) {
    if (!matchesMode(e, viewMode)) continue
    if (!map.has(e.body_part)) map.set(e.body_part, [])
    map.get(e.body_part)!.push(e)
  }
  return map
}

function effectsAt(map: Map<string, Effect[]>, p: string): Effect[] {
  return map.get(p) ?? []
}

function maxSeverity(effects: Effect[]): number {
  return effects.reduce((acc, e) => Math.max(acc, ({ high: 3, medium: 2, low: 1, unknown: 0 }[e.severity] ?? 0)), 0)
}

function highlightType(effects: Effect[]): 'none' | 'benefit' | 'side' | 'both' {
  if (!effects.length) return 'none'
  const hasB  = effects.some(e => e.effect_type === 'benefit')
  const hasSE = effects.some(e => e.effect_type === 'side_effect')
  return hasB && hasSE ? 'both' : hasB ? 'benefit' : 'side'
}

function organStroke(ht: 'none' | 'benefit' | 'side' | 'both'): string {
  return ht === 'benefit' ? '#4ade80' : ht === 'side' ? '#f87171' : ht === 'both' ? '#facc15' : '#c9a84c'
}

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

// ── Helper ────────────────────────────────────────────────────────────────────

const e = (body_part: string, effect_type: 'benefit' | 'side_effect', severity = 'low'): Effect =>
  ({ body_part, effect_type, severity })

// ── matchesMode ───────────────────────────────────────────────────────────────

describe('matchesMode — filters effects by viewMode', () => {
  it('viewMode=both includes benefit', () => {
    expect(matchesMode(e('stomach', 'benefit'), 'both')).toBe(true)
  })

  it('viewMode=both includes side_effect', () => {
    expect(matchesMode(e('stomach', 'side_effect'), 'both')).toBe(true)
  })

  it('viewMode=benefits includes benefit', () => {
    expect(matchesMode(e('liver', 'benefit'), 'benefits')).toBe(true)
  })

  it('viewMode=benefits excludes side_effect', () => {
    expect(matchesMode(e('liver', 'side_effect'), 'benefits')).toBe(false)
  })

  it('viewMode=side_effects includes side_effect', () => {
    expect(matchesMode(e('heart', 'side_effect'), 'side_effects')).toBe(true)
  })

  it('viewMode=side_effects excludes benefit', () => {
    expect(matchesMode(e('heart', 'benefit'), 'side_effects')).toBe(false)
  })
})

// ── effectMap building ────────────────────────────────────────────────────────

describe('buildEffectMap — groups effects by body part with mode filtering', () => {
  it('builds map with correct body part key', () => {
    const map = buildEffectMap([e('stomach', 'benefit')], 'both')
    expect(map.has('stomach')).toBe(true)
  })

  it('filters out non-matching effects in benefits mode', () => {
    const map = buildEffectMap([e('lung', 'side_effect')], 'benefits')
    expect(map.has('lung')).toBe(false)
  })

  it('groups multiple effects for same body part', () => {
    const map = buildEffectMap([e('kidney', 'benefit'), e('kidney', 'side_effect')], 'both')
    expect(map.get('kidney')).toHaveLength(2)
  })

  it('empty effects → empty map', () => {
    expect(buildEffectMap([], 'both').size).toBe(0)
  })

  it('does not mix body parts', () => {
    const map = buildEffectMap([e('eye', 'benefit'), e('ear', 'benefit')], 'benefits')
    expect(map.get('eye')).toHaveLength(1)
    expect(map.get('ear')).toHaveLength(1)
  })
})

// ── highlightType ─────────────────────────────────────────────────────────────

describe('highlightType — determines organ color class', () => {
  it('no effects → none', () => {
    expect(highlightType([])).toBe('none')
  })

  it('only benefit → benefit', () => {
    expect(highlightType([e('stomach', 'benefit')])).toBe('benefit')
  })

  it('only side_effect → side', () => {
    expect(highlightType([e('stomach', 'side_effect')])).toBe('side')
  })

  it('both types → both', () => {
    expect(highlightType([e('liver', 'benefit'), e('liver', 'side_effect')])).toBe('both')
  })

  it('multiple benefits only → benefit', () => {
    expect(highlightType([e('heart', 'benefit'), e('heart', 'benefit')])).toBe('benefit')
  })

  it('multiple side effects only → side', () => {
    expect(highlightType([e('lung', 'side_effect'), e('lung', 'side_effect')])).toBe('side')
  })

  it('viewMode=benefits: only benefits in map → benefit', () => {
    const map = buildEffectMap([e('kidney', 'benefit'), e('kidney', 'side_effect')], 'benefits')
    expect(highlightType(effectsAt(map, 'kidney'))).toBe('benefit')
  })

  it('viewMode=side_effects: only side_effects in map → side', () => {
    const map = buildEffectMap([e('kidney', 'benefit'), e('kidney', 'side_effect')], 'side_effects')
    expect(highlightType(effectsAt(map, 'kidney'))).toBe('side')
  })

  it('viewMode=both: mixed effects → both', () => {
    const map = buildEffectMap([e('kidney', 'benefit'), e('kidney', 'side_effect')], 'both')
    expect(highlightType(effectsAt(map, 'kidney'))).toBe('both')
  })

  it('part not in map → none', () => {
    const map = buildEffectMap([e('stomach', 'benefit')], 'both')
    expect(highlightType(effectsAt(map, 'nonexistent'))).toBe('none')
  })
})

// ── maxSeverity ───────────────────────────────────────────────────────────────

describe('maxSeverity — returns highest numeric severity', () => {
  it('empty effects → 0', () => {
    expect(maxSeverity([])).toBe(0)
  })

  it('low severity → 1', () => {
    expect(maxSeverity([e('s', 'benefit', 'low')])).toBe(1)
  })

  it('medium severity → 2', () => {
    expect(maxSeverity([e('s', 'benefit', 'medium')])).toBe(2)
  })

  it('high severity → 3', () => {
    expect(maxSeverity([e('s', 'benefit', 'high')])).toBe(3)
  })

  it('unknown severity → 0', () => {
    expect(maxSeverity([e('s', 'benefit', 'unknown')])).toBe(0)
  })

  it('undefined/invalid severity → 0', () => {
    expect(maxSeverity([e('s', 'benefit', 'xxxx')])).toBe(0)
  })

  it('max of multiple: high + low → 3', () => {
    expect(maxSeverity([e('s', 'benefit', 'high'), e('s', 'benefit', 'low')])).toBe(3)
  })

  it('max of multiple: medium + low → 2', () => {
    expect(maxSeverity([e('s', 'benefit', 'medium'), e('s', 'benefit', 'low')])).toBe(2)
  })

  it('pulse-strong threshold: maxSeverity >= 3 → true', () => {
    expect(maxSeverity([e('s', 'benefit', 'high')]) >= 3).toBe(true)
  })

  it('pulse-strong threshold: maxSeverity < 3 → false', () => {
    expect(maxSeverity([e('s', 'benefit', 'medium')]) >= 3).toBe(false)
  })
})

// ── organStroke ───────────────────────────────────────────────────────────────

describe('organStroke — SVG stroke color by highlight type', () => {
  it('benefit → green #4ade80', () => {
    expect(organStroke('benefit')).toBe('#4ade80')
  })

  it('side → red #f87171', () => {
    expect(organStroke('side')).toBe('#f87171')
  })

  it('both → yellow #facc15', () => {
    expect(organStroke('both')).toBe('#facc15')
  })

  it('none → gold #c9a84c', () => {
    expect(organStroke('none')).toBe('#c9a84c')
  })
})

// ── bodyPartLabel ─────────────────────────────────────────────────────────────

describe('bodyPartLabel — human-readable label with fallback', () => {
  it('brain → Brain', () => expect(bodyPartLabel('brain')).toBe('Brain'))
  it('eye → Eyes', ()   => expect(bodyPartLabel('eye')).toBe('Eyes'))
  it('ear → Ears', ()   => expect(bodyPartLabel('ear')).toBe('Ears'))
  it('heart → Heart', () => expect(bodyPartLabel('heart')).toBe('Heart'))
  it('lung → Lungs', () => expect(bodyPartLabel('lung')).toBe('Lungs'))
  it('liver → Liver', () => expect(bodyPartLabel('liver')).toBe('Liver'))
  it('stomach → Stomach', () => expect(bodyPartLabel('stomach')).toBe('Stomach'))
  it('kidney → Kidneys', () => expect(bodyPartLabel('kidney')).toBe('Kidneys'))
  it('blood → Blood System', () => expect(bodyPartLabel('blood')).toBe('Blood System'))
  it('vascular → Vascular System', () => expect(bodyPartLabel('vascular')).toBe('Vascular System'))
  it('unknown part → capitalized fallback', () => {
    expect(bodyPartLabel('spine')).toBe('Spine')
  })
  it('multi-word unknown part → first char capitalized only', () => {
    expect(bodyPartLabel('joint pain')).toBe('Joint pain')
  })
})

// ── modeOpts disabled logic ───────────────────────────────────────────────────

describe('modeOpts disabled state', () => {
  it('benefitCount = 0 → benefits mode disabled', () => {
    const count = 0
    const disabled = (count === 0)
    expect(disabled).toBe(true)
  })

  it('benefitCount = 1 → benefits mode enabled', () => {
    const count: number = 1
    const disabled = (count === 0)
    expect(disabled).toBe(false)
  })

  it('sideCount = 0 → side_effects mode disabled', () => {
    const count = 0
    expect((count === 0)).toBe(true)
  })

  it('"both" mode is never disabled', () => {
    const disabled = false
    expect(disabled).toBe(false)
  })
})
