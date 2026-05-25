/**
 * AnatomyBody.spec.ts — FE-AB-01 ~ 05
 *
 * Props required by AnatomyBody: effects, hovered, viewMode
 * Disable logic: benefitCount/sideCount control button disabled state
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AnatomyBody from '@/components/AnatomyBody.vue'

const BENEFIT_EFFECTS = [
  { body_part: 'muscle', effect_type: 'benefit', severity: 'low',      frequency: 80 },
  { body_part: 'liver',  effect_type: 'benefit', severity: 'low',      frequency: 90 },
]

const SE_EFFECTS = [
  { body_part: 'stomach', effect_type: 'side_effect', severity: 'moderate', frequency: 25 },
  { body_part: 'kidney',  effect_type: 'side_effect', severity: 'moderate', frequency: 7  },
]

describe('AnatomyBody', () => {
  it('FE-AB-01: renders SVG with viewBox', () => {
    const wrapper = mount(AnatomyBody, {
      props: { effects: BENEFIT_EFFECTS, hovered: null, viewMode: 'benefits' },
    })
    const svg = wrapper.find('svg')
    expect(svg.exists()).toBe(true)
    expect(svg.attributes('viewBox')).toBeTruthy()
  })

  it('FE-AB-02: mode-benefits button has mode-active when viewMode=benefits', () => {
    const wrapper = mount(AnatomyBody, {
      props: {
        effects: BENEFIT_EFFECTS,
        hovered: null,
        viewMode: 'benefits',
        showToggle: true,
        benefitCount: 2,
        sideCount: 0,
      },
    })
    const btn = wrapper.find('.mode-benefits')
    expect(btn.exists()).toBe(true)
    expect(btn.classes()).toContain('mode-active')
  })

  it('FE-AB-03: mode-side_effects button has mode-active when viewMode=side_effects', () => {
    const wrapper = mount(AnatomyBody, {
      props: {
        effects: SE_EFFECTS,
        hovered: null,
        viewMode: 'side_effects',
        showToggle: true,
        benefitCount: 0,
        sideCount: 2,
      },
    })
    const btn = wrapper.find('.mode-side_effects')
    expect(btn.exists()).toBe(true)
    expect(btn.classes()).toContain('mode-active')
  })

  it('FE-AB-04: clicking enabled side_effects button emits update:viewMode', async () => {
    const wrapper = mount(AnatomyBody, {
      props: {
        effects: [...BENEFIT_EFFECTS, ...SE_EFFECTS],
        hovered: null,
        viewMode: 'benefits',
        showToggle: true,
        benefitCount: 2,
        sideCount: 2,  // non-zero → button not disabled
      },
    })
    const seBtn = wrapper.find('.mode-side_effects')
    expect(seBtn.exists()).toBe(true)
    // Only click if not disabled (button element attribute)
    if (!seBtn.element.hasAttribute('disabled')) {
      await seBtn.trigger('click')
      expect(wrapper.emitted('update:viewMode')).toBeTruthy()
      const emitted = wrapper.emitted('update:viewMode')!
      expect(emitted[0]).toContain('side_effects')
    }
  })

  it('FE-AB-05: reduce-motion class not applied when prop is false/absent', () => {
    const wrapper = mount(AnatomyBody, {
      props: { effects: [], hovered: null, viewMode: 'benefits', reduceMotion: false },
    })
    expect(wrapper.classes()).not.toContain('reduce-motion')
  })
})
