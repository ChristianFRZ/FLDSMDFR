import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({ usuarios: vi.fn(), metricas: vi.fn() }))
vi.mock('../../api/users', () => ({ circuits: api.usuarios }))
vi.mock('../../api/metrics', () => ({ circuits: api.metricas }))

import EstadoCircuitos from '../EstadoCircuitos.vue'

const circuito = (target: string, state: string, extra = {}) => ({
  source: 'x',
  target,
  state,
  consecutive_failures: 0,
  since: new Date(Date.now() - 4000).toISOString(),
  retry_in_s: null,
  ...extra,
})

describe('EstadoCircuitos', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    api.usuarios.mockReset()
    api.metricas.mockReset()
  })
  afterEach(() => vi.useRealTimers())

  it('muestra los tres estados en español y la cuenta regresiva del abierto', async () => {
    api.usuarios.mockResolvedValue({
      instance: 'users-playlists-a1',
      circuits: [
        { ...circuito('catalog-streaming', 'open', { consecutive_failures: 5, retry_in_s: 7 }), source: 'users-playlists' },
      ],
    })
    api.metricas.mockResolvedValue({
      instance: 'playback-metrics-b2',
      circuits: [
        { ...circuito('catalog-streaming', 'half_open'), source: 'playback-metrics' },
        { ...circuito('users-playlists', 'closed'), source: 'playback-metrics' },
      ],
    })
    const w = mount(EstadoCircuitos)
    await flushPromises()
    expect(w.text()).toContain('Abierto')
    expect(w.text()).toContain('Semiabierto')
    expect(w.text()).toContain('Cerrado')
    expect(w.text()).toContain('vuelve a probar en 7 s')
    expect(w.text()).toContain('users-playlists → catalog-streaming')
    expect(w.text()).toContain('users-playlists-a1')
    w.unmount()
  })

  it('una mitad falla: "Sin datos de playback-metrics" y la otra sigue', async () => {
    api.usuarios.mockResolvedValue({
      instance: 'users-playlists-a1',
      circuits: [{ ...circuito('catalog-streaming', 'closed'), source: 'users-playlists' }],
    })
    api.metricas.mockRejectedValue(new Error('503'))
    const w = mount(EstadoCircuitos)
    await flushPromises()
    expect(w.text()).toContain('Sin datos de playback-metrics')
    expect(w.text()).toContain('users-playlists → catalog-streaming')
    w.unmount()
  })

  it('se refresca cada 2 s y se detiene al desmontar', async () => {
    api.usuarios.mockResolvedValue({ instance: 'a', circuits: [] })
    api.metricas.mockResolvedValue({ instance: 'b', circuits: [] })
    const w = mount(EstadoCircuitos)
    await flushPromises()
    expect(api.usuarios).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(2000)
    expect(api.usuarios).toHaveBeenCalledTimes(2)
    w.unmount()
    await vi.advanceTimersByTimeAsync(6000)
    expect(api.usuarios).toHaveBeenCalledTimes(2)
  })

  it('no refresca mientras la pestaña está oculta', async () => {
    api.usuarios.mockResolvedValue({ instance: 'a', circuits: [] })
    api.metricas.mockResolvedValue({ instance: 'b', circuits: [] })
    const w = mount(EstadoCircuitos)
    await flushPromises()
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => true })
    document.dispatchEvent(new Event('visibilitychange'))
    await vi.advanceTimersByTimeAsync(6000)
    expect(api.usuarios).toHaveBeenCalledTimes(1)
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => false })
    document.dispatchEvent(new Event('visibilitychange'))
    await flushPromises()
    expect(api.usuarios).toHaveBeenCalledTimes(2)
    w.unmount()
  })
})
