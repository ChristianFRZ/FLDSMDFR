import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import type { PlaylistDetail } from '../../api/types'

const api = vi.hoisted(() => ({
  get: vi.fn(),
  list: vi.fn(),
  removeSong: vi.fn(),
  reorder: vi.fn(),
  createInvite: vi.fn(),
  mostrar: vi.fn(),
  play: vi.fn(),
}))
vi.mock('../../api/playlists', () => ({
  get: api.get,
  list: api.list,
  removeSong: api.removeSong,
  reorder: api.reorder,
  createInvite: api.createInvite,
  coverUrl: (id: string) => `/c/${id}`,
}))
vi.mock('../../composables/useAvisos', () => ({ useAvisos: () => ({ mostrar: api.mostrar }) }))
vi.mock('../../composables/usePlayer', () => ({
  usePlayer: () => ({ play: api.play, current: ref(null), enqueue: vi.fn(), playNext: vi.fn() }),
}))
vi.mock('../../composables/useSession', () => ({
  useSession: () => ({ user: ref({ id: 'u1', name: 'Ana', email: 'a@b.mx', role: 'listener' }) }),
}))

const detalle = (extra: Partial<PlaylistDetail> = {}): PlaylistDetail => ({
  id: 'p1',
  name: 'Viaje',
  songs: [
    { song_id: 's1', title: 'Granizo', artist: 'Meteoros', album: 'A', duration_seconds: 60, position: 0, status: 'ok' },
    { song_id: 's2', title: 'Monzón', artist: 'Meteoros', album: 'A', duration_seconds: 60, position: 1, status: 'ok' },
  ],
  total_seconds: 120,
  has_cover: false,
  role: 'owner',
  members: [],
  ...extra,
})

async function montar() {
  vi.resetModules()
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<p />' } },
      { path: '/casete/:id', component: { template: '<p />' } },
    ],
  })
  await router.push('/casete/p1')
  const CaseteView = (await import('../CaseteView.vue')).default
  const { ApiError } = await import('../../api/http')
  const w = mount(CaseteView, { global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  return { w, router, ApiError }
}

describe('CaseteView', () => {
  beforeEach(() => {
    for (const f of Object.values(api)) f.mockReset()
    api.get.mockResolvedValue(detalle())
    api.list.mockResolvedValue([])
  })

  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('muestra el casete y "Reproducir todo" usa la lista como cola', async () => {
    const { w } = await montar()
    expect(w.get('h1').text()).toBe('Viaje')
    await w.get('button[data-prueba="reproducir-todo"]').trigger('click')
    const [primera, cola] = api.play.mock.calls[0]
    expect(primera.id).toBe('s1')
    expect(cola.map((s: { id: string }) => s.id)).toEqual(['s1', 's2'])
    w.unmount()
  })

  it('bajar una canción pide el orden nuevo', async () => {
    api.reorder.mockResolvedValue(detalle())
    const { w } = await montar()
    await w.get('button[aria-label="Bajar «Granizo»"]').trigger('click')
    await flushPromises()
    expect(api.reorder).toHaveBeenCalledWith('p1', ['s2', 's1'])
    w.unmount()
  })

  it('404 on write shows lost access and goes home', async () => {
    const { w, router, ApiError } = await montar()
    api.removeSong.mockRejectedValue(new ApiError(404, 'playlist_not_found', 'x'))
    await w.get('button[aria-label="Quitar «Granizo» del casete"]').trigger('click')
    await flushPromises()
    expect(api.mostrar).toHaveBeenCalledWith('Ya no tienes acceso a este casete.', 'error')
    expect(api.list).toHaveBeenCalled()
    expect(router.currentRoute.value.fullPath).toBe('/')
    w.unmount()
  })

  it('copy link uses absolute url', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    api.createInvite.mockResolvedValue({ token: 'tok', url: '/invitacion/tok' })
    const { w } = await montar()
    await w.get('button[data-prueba="generar-enlace"]').trigger('click')
    await flushPromises()
    const absoluto = `${location.origin}/invitacion/tok`
    expect((w.get('input[aria-label="Enlace de invitación"]').element as HTMLInputElement).value).toBe(absoluto)
    await w.get('button[data-prueba="copiar-enlace"]').trigger('click')
    await flushPromises()
    expect(writeText).toHaveBeenCalledWith(absoluto)
    w.unmount()
  })

  it('un colaborador no ve compartir ni borrar, pero puede salir', async () => {
    api.get.mockResolvedValue(detalle({ role: 'collaborator', members: [{ user_id: 'u1', name: 'Ana' }] }))
    const { w } = await montar()
    expect(w.find('button[data-prueba="generar-enlace"]').exists()).toBe(false)
    expect(w.find('button[data-prueba="borrar-casete"]').exists()).toBe(false)
    expect(w.find('button[data-prueba="salir-casete"]').exists()).toBe(true)
    w.unmount()
  })

  it('una canción degradada se muestra "Sin actualizar" y no se reproduce', async () => {
    api.get.mockResolvedValue(
      detalle({
        songs: [
          { song_id: 's1', title: 'Granizo', artist: 'Meteoros', album: 'A', duration_seconds: 60, position: 0, status: 'degraded' },
        ],
      }),
    )
    const { w } = await montar()
    expect(w.text()).toContain('Sin actualizar')
    await w.get('[data-prueba="reproducir"]').trigger('click')
    expect(api.play).not.toHaveBeenCalled()
    w.unmount()
  })
})
