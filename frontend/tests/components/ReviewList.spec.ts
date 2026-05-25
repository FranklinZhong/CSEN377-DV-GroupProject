/**
 * ReviewList.spec.ts — FE-RL-01 ~ 04
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { api } from '@/api/client'

vi.mock('@/api/client', () => ({
  api: {
    getReviewsList: vi.fn(),
  },
}))

import ReviewList from '@/components/ReviewList.vue'

const REVIEWS = [
  { id: 1, rating: 4.5, sentiment: 'positive', review_text: 'Works well', body_parts: ['stomach'], source: 'WebMD' },
  { id: 2, rating: 2.0, sentiment: 'negative', review_text: 'Had cramps', body_parts: ['stomach'], source: 'WebMD' },
]

const mockResponse = (reviews = REVIEWS, total = 15, total_pages = 2) => ({
  data: {
    success: true,
    data: { reviews, total, total_pages, page: 1, page_size: 10 },
  },
})

async function flushAsync() {
  await new Promise(r => setTimeout(r, 0))
}

const STUBS = { ElInput: true, ElSelect: true, ElOption: true, ElButton: true, ElSkeleton: true }

describe('ReviewList', () => {
  beforeEach(() => {
    vi.mocked(api.getReviewsList).mockResolvedValue(mockResponse() as any)
  })

  it('FE-RL-01: renders pagination when totalPages > 1', async () => {
    const wrapper = mount(ReviewList, {
      props: { drugId: 1 },
      global: { stubs: STUBS },
    })
    await flushAsync()
    await wrapper.vm.$nextTick()
    const pager = wrapper.find('.rl-pager')
    expect(pager.exists()).toBe(true)
  })

  it('FE-RL-02: calls api.getReviewsList on mount', async () => {
    mount(ReviewList, {
      props: { drugId: 1 },
      global: { stubs: STUBS },
    })
    await flushAsync()
    expect(vi.mocked(api.getReviewsList)).toHaveBeenCalledWith(1, expect.objectContaining({ page: 1 }))
  })

  it('FE-RL-03: shows empty message when no reviews', async () => {
    vi.mocked(api.getReviewsList).mockResolvedValue(mockResponse([], 0, 0) as any)
    const wrapper = mount(ReviewList, {
      props: { drugId: 1 },
      global: { stubs: STUBS },
    })
    await flushAsync()
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('No reviews match')
  })

  it('FE-RL-04: initialBodyPart prop passed to first API call', async () => {
    mount(ReviewList, {
      props: { drugId: 1, initialBodyPart: 'stomach' },
      global: { stubs: STUBS },
    })
    await flushAsync()
    expect(vi.mocked(api.getReviewsList)).toHaveBeenCalledWith(
      1,
      expect.objectContaining({ body_part: 'stomach' }),
    )
  })
})
