import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

const api = vi.hoisted(() => ({ history: vi.fn(), play: vi.fn() }))
vi.mock('../../api/me', () => ({ history: api.history }))
vi.mock('../../composables/useFavoritos', () => ({
  useFavoritos: () => ({ esFavorita: () => false, alternar: vi.fn() }),
}))
vi.mock('../../composables/usePlayer', () => ({
  usePlayer: () => ({ play: api.play, current: ref(null), enqueue: vi.fn(), playNext: vi.fn() }),
}))

import HistorialView from '../HistorialView.vue'

describe('HistorialView', () => {
  it('con el catálogo caído muestra el aviso y las copias "Sin actualizar"', async () => {
    api.history.mockResolvedValue({
      items: [
        {
          song: {
            id: 's1',
            title: 'Granizo',
            artist: 'Meteoros',
            album: 'A',
            duration_seconds: 60,
            is_active: false,
            has_cover: false,
          },
          last_played_at: '2026-10-30T00:00:00Z',
          available: false,
          status: 'degraded',
        },
      ],
      total: 1,
      degraded: true,
    })
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { template: '<p />' } }] })
    const w = mount(HistorialView, { global: { plugins: [router] } })
    await flushPromises()
    expect(w.text()).toContain('El catálogo no responde; mostramos los últimos datos guardados.')
    expect(w.text()).toContain('Sin actualizar')
  })
})
