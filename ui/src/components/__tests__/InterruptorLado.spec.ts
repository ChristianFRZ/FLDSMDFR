import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'
import InterruptorLado from '../InterruptorLado.vue'
import { useTheme } from '../../composables/useTheme'

describe('InterruptorLado', () => {
  beforeEach(() => {
    useTheme().set('A')
  })

  it('es un switch accesible que muestra el lado actual', () => {
    const wrapper = mount(InterruptorLado)
    const button = wrapper.get('button')
    expect(button.attributes('role')).toBe('switch')
    expect(button.attributes('aria-checked')).toBe('false')
    expect(button.text()).toContain('Lado A')
    expect(button.attributes('title')).toBe('Cambiar a Lado B')
  })

  it('al pulsarlo cambia al Lado B', async () => {
    const wrapper = mount(InterruptorLado)
    await wrapper.get('button').trigger('click')
    const button = wrapper.get('button')
    expect(button.attributes('aria-checked')).toBe('true')
    expect(button.text()).toContain('Lado B')
    expect(useTheme().side.value).toBe('B')
    expect(document.documentElement.dataset.lado).toBe('B')
  })
})
