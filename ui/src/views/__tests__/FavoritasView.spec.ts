import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

const api = vi.hoisted(() => ({ favorites: vi.fn(), play: vi.fn() }))
vi.mock('../../api/me', () => ({ favorites: api.favorites }))
vi.mock('../../composables/useFavoritos', () => ({
  useFavoritos: () => ({ version: ref(0), esFavorita: () => true, alternar: vi.fn() }),
}))
vi.mock('../../composables/usePlayer', () => ({
  usePlayer: () => ({ play: api.play, current: ref(null), enqueue: vi.fn(), playNext: vi.fn() }),
}))

import FavoritasView from '../FavoritasView.vue'

describe('FavoritasView', () => {
  it('con el catálogo caído muestra el aviso y las copias "Sin actualizar"', async () => {
    api.favorites.mockResolvedValue({
      songs: [
        {
          song_id: 's1',
          title: 'Granizo',
          artist: 'Meteoros',
          album: 'A',
          duration_seconds: 60,
          has_cover: false,
          status: 'degraded',
          added_at: '2026-10-30T00:00:00Z',
        },
      ],
      total_seconds: 60,
      degraded: true,
    })
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { template: '<p />' } }] })
    const w = mount(FavoritasView, { global: { plugins: [router] } })
    await flushPromises()
    expect(w.text()).toContain('El catálogo no responde; mostramos los últimos datos guardados.')
    expect(w.text()).toContain('Granizo')
    expect(w.text()).toContain('Sin actualizar')
    await w.get('[data-prueba="reproducir"]').trigger('click')
    expect(api.play).not.toHaveBeenCalled()
  })
})
