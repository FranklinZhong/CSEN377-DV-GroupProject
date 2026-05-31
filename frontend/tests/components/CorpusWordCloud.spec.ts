/**
 * CorpusWordCloud.spec.ts — body-mapped word cloud component
 *
 * Verifies that the component:
 *  - Mounts with an SVG and body silhouette
 *  - Calls api.getCorpusNlp() on mount
 *  - Renders one organ group per ORGANS entry when data is present
 *  - Renders <text> nodes whose content matches the mocked TF-IDF terms
 *  - Shows an error state when the API fails
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CorpusWordCloud from '@/components/CorpusWordCloud.vue'
import { ORGANS } from '@/data/anatomyOrgans'

vi.mock('@/api/client', () => ({
  api: {
    getCorpusNlp: vi.fn(),
  },
}))

import { api } from '@/api/client'

function mockTfidfResponse() {
  const tfidf: Record<string, { term: string; score_norm: number; rank: number }[]> = {}
  for (const o of ORGANS) {
    tfidf[o.key] = [
      { term: `${o.key}-pain`,     score_norm: 1.0,  rank: 1 },
      { term: `${o.key}-symptom`,  score_norm: 0.7,  rank: 2 },
      { term: `${o.key}-effect`,   score_norm: 0.5,  rank: 3 },
    ]
  }
  return {
    data: {
      success: true,
      data: {
        tfidf,
        sentiment: [],
      },
      meta: { source: 'test', data_version: '1', confidence: 'high', report_count: null },
      warnings: [],
    },
  }
}

describe('CorpusWordCloud', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('FE-CWC-01: renders an SVG with 420×780 viewBox and body silhouette', async () => {
    ;(api.getCorpusNlp as ReturnType<typeof vi.fn>).mockResolvedValue(mockTfidfResponse())
    const wrapper = mount(CorpusWordCloud)
    await flushPromises()

    const svg = wrapper.find('svg.wc-svg')
    expect(svg.exists()).toBe(true)
    expect(svg.attributes('viewBox')).toBe('0 0 420 780')

    // Silhouette path is rendered (twice — fill + stroke)
    const silhouettePaths = wrapper.findAll('.wc-silhouette path')
    expect(silhouettePaths.length).toBeGreaterThanOrEqual(2)
  })

  it('FE-CWC-02: calls api.getCorpusNlp on mount', async () => {
    ;(api.getCorpusNlp as ReturnType<typeof vi.fn>).mockResolvedValue(mockTfidfResponse())
    mount(CorpusWordCloud)
    await flushPromises()
    expect(api.getCorpusNlp).toHaveBeenCalledTimes(1)
  })

  it('FE-CWC-03: renders one organ group per ORGANS entry', async () => {
    ;(api.getCorpusNlp as ReturnType<typeof vi.fn>).mockResolvedValue(mockTfidfResponse())
    const wrapper = mount(CorpusWordCloud)
    await flushPromises()

    const groups = wrapper.findAll('.organ-group')
    expect(groups.length).toBe(ORGANS.length)
  })

  it('FE-CWC-04: renders mocked TF-IDF terms inside organ groups', async () => {
    ;(api.getCorpusNlp as ReturnType<typeof vi.fn>).mockResolvedValue(mockTfidfResponse())
    const wrapper = mount(CorpusWordCloud)
    await flushPromises()

    // The mock injects terms like "brain-pain", "heart-pain", etc.
    // At least the top-ranked (largest) term should be present for each organ.
    const html = wrapper.html()
    const found = ORGANS.filter(o => html.includes(`${o.key}-pain`)).length
    // Some very-narrow zones may legitimately drop terms; accept ≥ 80% coverage.
    expect(found).toBeGreaterThanOrEqual(Math.floor(ORGANS.length * 0.8))
  })

  it('FE-CWC-05: shows error message when API call fails', async () => {
    ;(api.getCorpusNlp as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('network'))
    const wrapper = mount(CorpusWordCloud)
    await flushPromises()

    expect(wrapper.classes()).toContain('is-error')
    expect(wrapper.text()).toMatch(/FAILED/i)
  })

  it('FE-CWC-06: shows error when API returns success=false', async () => {
    ;(api.getCorpusNlp as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { success: false, error: { code: 'X', message: 'oops' } },
    })
    const wrapper = mount(CorpusWordCloud)
    await flushPromises()
    expect(wrapper.classes()).toContain('is-error')
  })
})
