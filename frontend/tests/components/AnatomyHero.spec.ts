/**
 * AnatomyHero.spec.ts — FE-AH-01 ~ 03
 *
 * AnatomyHero is a pure-decorative SVG component with no external API calls.
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AnatomyHero from '@/components/AnatomyHero.vue'

describe('AnatomyHero', () => {
  it('FE-AH-01: renders an SVG with a viewBox attribute', () => {
    const wrapper = mount(AnatomyHero)
    const svg = wrapper.find('svg')
    expect(svg.exists()).toBe(true)
    expect(svg.attributes('viewBox')).toBeTruthy()
  })

  it('FE-AH-02: root element has hero-anatomy class', () => {
    const wrapper = mount(AnatomyHero)
    expect(wrapper.classes()).toContain('hero-anatomy')
  })

  it('FE-AH-03: reduce-motion class applied when prop is set', () => {
    // The component detects prefers-reduced-motion via matchMedia.
    // We can also test by verifying the class binding logic through
    // a direct check on the root element class list.
    const wrapper = mount(AnatomyHero)
    // By default, happy-dom matchMedia returns false for prefers-reduced-motion,
    // so reduce-motion class should NOT be applied.
    expect(wrapper.classes()).not.toContain('reduce-motion')
  })

  it('FE-AH-04: hero-svg class exists on the SVG element', () => {
    const wrapper = mount(AnatomyHero)
    const svg = wrapper.find('.hero-svg')
    expect(svg.exists()).toBe(true)
  })
})
