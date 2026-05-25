/**
 * TugOfWarChart.spec.ts — FE-TOW-01 ~ 04
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'

// Mock api before importing the component
vi.mock('@/api/client', () => ({
  api: {
    getReviews: vi.fn(),
  },
}))

import TugOfWarChart from '@/components/TugOfWarChart.vue'

const CLUSTERS = [
  { body_part: 'stomach', sentiment: 'positive', review_count: 150, top_terms: ['effective'], representative_quotes: [] },
  { body_part: 'stomach', sentiment: 'negative', review_count: 80,  top_terms: ['cramps'],    representative_quotes: [] },
  { body_part: 'kidney',  sentiment: 'positive', review_count: 30,  top_terms: ['kidneys'],   representative_quotes: [] },
]

async function flushAsync() {
  // let the watch() + load() promise settle
  await new Promise(r => setTimeout(r, 0))
}

describe('TugOfWarChart', () => {
  beforeEach(() => {
    // @ts-ignore
    const { api } = require('@/api/client')
    api.getReviews.mockResolvedValue({
      data: { success: true, data: { clusters: CLUSTERS } },
    })
  })

  it('FE-TOW-01: renders one row per distinct body_part', async () => {
    const wrapper = mount(TugOfWarChart, {
      props: { drugId: 1 },
      global: { stubs: { ElDrawer: true, ElSkeleton: true } },
    })
    await flushAsync()
    await wrapper.vm.$nextTick()
    const rows = wrapper.findAll('.tow-row')
    // stomach + kidney = 2 distinct body parts
    expect(rows.length).toBe(2)
  })

  it('FE-TOW-02: shows empty state when no clusters', async () => {
    // @ts-ignore
    const { api } = require('@/api/client')
    api.getReviews.mockResolvedValue({
      data: { success: true, data: { clusters: [] } },
    })
    const wrapper = mount(TugOfWarChart, {
      props: { drugId: 99 },
      global: { stubs: { ElDrawer: true, ElSkeleton: true } },
    })
    await flushAsync()
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('No patient review data')
  })

  it('FE-TOW-03: clicking a row opens the drawer', async () => {
    const wrapper = mount(TugOfWarChart, {
      props: { drugId: 1 },
      global: { stubs: { ElDrawer: true, ElSkeleton: true, ReviewList: true } },
    })
    await flushAsync()
    await wrapper.vm.$nextTick()
    const row = wrapper.find('.tow-row')
    if (row.exists()) {
      await row.trigger('click')
      // @ts-ignore – expose internal state via vm
      expect((wrapper.vm as any).drawerOpen).toBe(true)
    }
  })

  it('FE-TOW-04: mousing over a row emits highlight', async () => {
    const wrapper = mount(TugOfWarChart, {
      props: { drugId: 1 },
      global: { stubs: { ElDrawer: true, ElSkeleton: true } },
    })
    await flushAsync()
    await wrapper.vm.$nextTick()
    const row = wrapper.find('.tow-row')
    if (row.exists()) {
      await row.trigger('mouseenter')
      expect(wrapper.emitted('highlight')).toBeTruthy()
    }
  })
})
