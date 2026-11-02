import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { bitrateKbps } from '../../composables/streaming'
import VentanaCarretes from '../VentanaCarretes.vue'

function movimientoReducido(reducido: boolean) {
  vi.stubGlobal('matchMedia', (q: string) => ({
    matches: reducido && q.includes('reduce'),
    media: q,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }))
}

describe('VentanaCarretes', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('reels stop when paused and with reduced motion', () => {
    movimientoReducido(false)
    expect(mount(VentanaCarretes, { props: { girando: true } }).classes()).toContain('carretes--girando')
    expect(mount(VentanaCarretes, { props: { girando: false } }).classes()).not.toContain('carretes--girando')
    movimientoReducido(true)
    expect(mount(VentanaCarretes, { props: { girando: true } }).classes()).not.toContain('carretes--girando')
  })
})

describe('bitrateKbps', () => {
  it('estima kbps con tamaño y duración', () => {
    expect(bitrateKbps(4_000_000, 250)).toBe(128)
  })

  it('sin duración o tamaño no estima', () => {
    expect(bitrateKbps(0, 120)).toBeNull()
    expect(bitrateKbps(4_000_000, 0)).toBeNull()
  })
})
