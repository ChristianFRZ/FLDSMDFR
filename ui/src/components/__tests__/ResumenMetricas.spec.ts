import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({ summary: vi.fn() }))
vi.mock('../../api/metrics', () => ({ summary: api.summary }))

import ResumenMetricas from '../ResumenMetricas.vue'

describe('ResumenMetricas', () => {
  it('un total en null se muestra como "—" con la nota "sin datos"', async () => {
    api.summary.mockResolvedValue({
      total_playbacks: 12,
      total_songs: 30,
      total_users: null,
      top: [],
      degraded: true,
    })
    const w = mount(ResumenMetricas)
    await flushPromises()
    const usuarios = w.get('[data-prueba="total-usuarios"]')
    expect(usuarios.text()).toContain('—')
    expect(usuarios.text()).toContain('sin datos')
    expect(w.get('[data-prueba="total-canciones"]').text()).toContain('30')
  })
})
