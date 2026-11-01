import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import type { PlaylistSummary } from '../../api/types'

const api = vi.hoisted(() => ({ list: vi.fn(), create: vi.fn(), follows: vi.fn() }))
vi.mock('../../api/playlists', () => ({ list: api.list, create: api.create, addSong: vi.fn() }))
vi.mock('../../api/me', () => ({ follows: api.follows, follow: vi.fn(), unfollow: vi.fn(), favoriteIds: vi.fn() }))
vi.mock('../../composables/useAvisos', () => ({ useAvisos: () => ({ mostrar: vi.fn() }) }))

const resumen = (id: string, name: string, extra: Partial<PlaylistSummary> = {}): PlaylistSummary => ({
  id,
  name,
  song_count: 4,
  updated_at: '2026-10-30T00:00:00Z',
  has_cover: false,
  role: 'owner',
  ...extra,
})

async function montar() {
  vi.resetModules()
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<p />' } },
      { path: '/casete/:id', component: { template: '<p />' } },
      { path: '/favoritas', component: { template: '<p />' } },
      { path: '/catalogo', component: { template: '<p />' } },
    ],
  })
  await router.push('/')
  const { useCasetes } = await import('../../composables/useCasetes')
  await useCasetes().cargar()
  const Biblioteca = (await import('../Biblioteca.vue')).default
  const w = mount(Biblioteca, { global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  return { w, router }
}

describe('Biblioteca', () => {
  beforeEach(() => {
    for (const f of Object.values(api)) f.mockReset()
    api.list.mockResolvedValue([resumen('a', 'Viaje'), resumen('b', 'Club', { role: 'collaborator' })])
    api.follows.mockResolvedValue([
      { artist: 'Lila Downs', followed_at: '2026-10-01T00:00:00Z', song_count: 3, cover_song_id: null },
    ])
  })

  it('lista favoritas primero y los casetes con su detalle', async () => {
    const { w } = await montar()
    const filas = w.findAll('[data-prueba="fila-biblioteca"]').map((f) => f.text())
    expect(filas[0]).toContain('Tus favoritas')
    expect(filas[1]).toContain('Casete · 4 canciones')
    expect(filas[2]).toContain('Casete · Colaborativo')
    w.unmount()
  })

  it('create inline navigates', async () => {
    api.create.mockResolvedValue(resumen('n', 'Fiesta', { song_count: 0 }))
    const { w, router } = await montar()
    await w.get('button[aria-label="Crear casete"]').trigger('click')
    const campo = w.get('input[aria-label="Nombre del casete nuevo"]')
    await campo.setValue('Fiesta')
    await campo.trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(api.create).toHaveBeenCalledWith('Fiesta')
    expect(router.currentRoute.value.fullPath).toBe('/casete/n')
    w.unmount()
  })

  it('Esc cancela el casete nuevo', async () => {
    const { w } = await montar()
    await w.get('button[aria-label="Crear casete"]').trigger('click')
    await w.get('input[aria-label="Nombre del casete nuevo"]').trigger('keydown', { key: 'Escape' })
    expect(w.find('input[aria-label="Nombre del casete nuevo"]').exists()).toBe(false)
    expect(api.create).not.toHaveBeenCalled()
    w.unmount()
  })

  it('tabs keyboard navigation', async () => {
    const { w } = await montar()
    const casetes = w.get('[role="tab"]#pestana-casetes')
    await casetes.trigger('keydown', { key: 'ArrowRight' })
    await flushPromises()
    const artistas = w.get('[role="tab"]#pestana-artistas')
    expect(artistas.attributes('aria-selected')).toBe('true')
    expect(document.activeElement).toBe(artistas.element)
    expect(w.text()).toContain('Lila Downs')
    expect(w.text()).toContain('Artista · 3 temas')
    w.unmount()
  })
})
