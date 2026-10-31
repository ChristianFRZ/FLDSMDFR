import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import BarraProgreso from '../BarraProgreso.vue'

const props = { duration: 200, currentTime: 10, buffered: [[0, 50], [100, 150]] as Array<[number, number]> }

describe('BarraProgreso', () => {
  it('dibuja un segmento por rango descargado', () => {
    const segmentos = mount(BarraProgreso, { props }).findAll('.segmento-descargado')
    expect(segmentos).toHaveLength(2)
    expect(segmentos[0].attributes('style')).toContain('left: 0%')
    expect(segmentos[0].attributes('style')).toContain('width: 25%')
    expect(segmentos[1].attributes('style')).toContain('left: 50%')
    expect(segmentos[1].attributes('style')).toContain('width: 25%')
  })

  it('expone el slider accesible', () => {
    const slider = mount(BarraProgreso, { props }).get('[role="slider"]')
    expect(slider.attributes('aria-valuemin')).toBe('0')
    expect(slider.attributes('aria-valuemax')).toBe('200')
    expect(slider.attributes('aria-valuenow')).toBe('10')
    expect(slider.attributes('aria-valuetext')).toBe('0:10 de 3:20')
  })

  it('ArrowRight emite seek +5 s y ArrowLeft -5 s', async () => {
    const wrapper = mount(BarraProgreso, { props })
    await wrapper.get('[role="slider"]').trigger('keydown', { key: 'ArrowRight' })
    await wrapper.get('[role="slider"]').trigger('keydown', { key: 'ArrowLeft' })
    expect(wrapper.emitted('seek')).toEqual([[15], [5]])
  })

  it('Home y End saltan a los extremos; el seek se limita al rango', async () => {
    const wrapper = mount(BarraProgreso, { props: { ...props, currentTime: 198 } })
    const slider = wrapper.get('[role="slider"]')
    await slider.trigger('keydown', { key: 'Home' })
    await slider.trigger('keydown', { key: 'End' })
    await slider.trigger('keydown', { key: 'ArrowRight' })
    expect(wrapper.emitted('seek')).toEqual([[0], [200], [200]])
  })

  it('clic emite seek proporcional', async () => {
    const wrapper = mount(BarraProgreso, { props })
    const slider = wrapper.get('[role="slider"]')
    slider.element.getBoundingClientRect = () =>
      ({ left: 100, width: 400, top: 0, height: 40, right: 500, bottom: 40, x: 100, y: 0 }) as DOMRect
    await slider.trigger('click', { clientX: 300 })
    expect(wrapper.emitted('seek')).toEqual([[100]])
  })

  it('sin duración no emite ni se puede mover', async () => {
    const wrapper = mount(BarraProgreso, { props: { duration: 0, currentTime: 0, buffered: [] } })
    const slider = wrapper.get('[role="slider"]')
    expect(slider.attributes('aria-disabled')).toBe('true')
    await slider.trigger('keydown', { key: 'ArrowRight' })
    expect(wrapper.emitted('seek')).toBeUndefined()
  })
})
