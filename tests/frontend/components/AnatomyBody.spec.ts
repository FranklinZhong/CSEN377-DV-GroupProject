/**
 * AnatomyBody.spec.ts — FE-AB-01 ~ 05
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AnatomyBody from '@/components/AnatomyBody.vue'

const BENEFIT_EFFECTS = [
  { body_part: 'muscle', effect_type: 'benefit', severity: 'low', frequency: 80 },
  { body_part: 'liver',  effect_type: 'benefit', severity: 'low', frequency: 90 },
]

const SE_EFFECTS = [
  { body_part: 'stomach', effect_type: 'side_effect', severity: 'moderate', frequency: 25 },
  { body_part: 'kidney',  effect_type: 'side_effect', severity: 'moderate', frequency: 7 },
]

describe('AnatomyBody', () => {
  it('FE-AB-01: renders SVG with viewBox', () => {
    const wrapper = mount(AnatomyBody, {
      props: { effects: BENEFIT_EFFECTS, viewMode: 'benefits' },
    })
    const svg = wrapper.find('svg')
    expect(svg.exists()).toBe(true)
    expect(svg.attributes('viewBox')).toBeTruthy()
  })

  it('FE-AB-02: mode-benefits button is active in benefits mode', () => {
    const wrapper = mount(AnatomyBody, {
      props: { effects: BENEFIT_EFFECTS, viewMode: 'benefits', showToggle: true },
    })
    const btn = wrapper.find('.mode-benefits')
    expect(btn.exists()).toBe(true)
    expect(btn.classes()).toContain('mode-active')
  })

  it('FE-AB-03: mode-side_effects button is active in side_effects mode', () => {
    const wrapper = mount(AnatomyBody, {
      props: { effects: SE_EFFECTS, viewMode: 'side_effects', showToggle: true },
    })
    const btn = wrapper.find('.mode-side_effects')
    expect(btn.exists()).toBe(true)
    expect(btn.classes()).toContain('mode-active')
  })

  it('FE-AB-04: clicking a mode button emits update:viewMode', async () => {
    const wrapper = mount(AnatomyBody, {
      props: {
        effects: [...BENEFIT_EFFECTS, ...SE_EFFECTS],
        viewMode: 'benefits',
        showToggle: true,
      },
    })
    const seBtn = wrapper.find('.mode-side_effects')
    if (seBtn.exists() && !seBtn.attributes('disabled')) {
      await seBtn.trigger('click')
      expect(wrapper.emitted('update:viewMode')).toBeTruthy()
      expect(wrapper.emitted('update:viewMode')![0]).toContain('side_effects')
    }
  })

  it('FE-AB-05: reduce-motion class not applied by default', () => {
    const wrapper = mount(AnatomyBody, {
      props: { effects: [], viewMode: 'benefits' },
    })
    expect(wrapper.classes()).not.toContain('reduce-motion')
  })
})
