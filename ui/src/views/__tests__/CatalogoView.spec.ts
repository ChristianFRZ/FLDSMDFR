import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import type { SongOut } from '../../api/types'

const api = vi.hoisted(() => ({
  list: vi.fn(),
  play: vi.fn(),
  follows: vi.fn(),
  follow: vi.fn(),
  unfollow: vi.fn(),
}))
vi.mock('../../api/songs', () => ({ list: api.list, coverUrl: (id: string) => `/c/${id}` }))
vi.mock('../../api/me', () => ({
  follows: api.follows,
  follow: api.follow,
  unfollow: api.unfollow,
  favoriteIds: vi.fn(),
  like: vi.fn(),
  unlike: vi.fn(),
}))
vi.mock('../../composables/usePlayer', () => ({
  usePlayer: () => ({ play: api.play, current: ref(null), enqueue: vi.fn(), playNext: vi.fn() }),
}))
vi.mock('../../composables/useAvisos', () => ({ useAvisos: () => ({ mostrar: vi.fn() }) }))

const cancion = (id: string, title: string, artist = 'Los Meteoros'): SongOut => ({
  id,
  title,
  artist,
  album: 'Pronóstico',
  duration_seconds: 192,
  is_active: true,
  has_cover: false,
})

async function montar(ruta = '/catalogo') {
  vi.resetModules()
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/catalogo', component: { template: '<p />' } }],
  })
  await router.push(ruta)
  const CatalogoView = (await import('../CatalogoView.vue')).default
  const w = mount(CatalogoView, { global: { plugins: [router] } })
  await flushPromises()
  return { w, router }
}

describe('CatalogoView', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    for (const f of Object.values(api)) f.mockReset()
    api.follows.mockResolvedValue([])
    api.follow.mockResolvedValue(undefined)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('reads q from route', async () => {
    api.list.mockResolvedValue({ items: [], total: 0 })
    const { w } = await montar('/catalogo?q=lluvia')
    expect(api.list).toHaveBeenCalledWith('lluvia', 0)
    expect((w.get('input[type="search"]').element as HTMLInputElement).value).toBe('lluvia')
  })

  it('busca 250 ms después de escribir y refleja la búsqueda en ?q=', async () => {
    api.list.mockResolvedValue({ items: [], total: 0 })
    const { w, router } = await montar()
    api.list.mockClear()
    for (const parcial of ['l', 'll', 'llu']) await w.get('input[type="search"]').setValue(parcial)
    await vi.advanceTimersByTimeAsync(249)
    expect(api.list).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(1)
    await flushPromises()
    expect(api.list).toHaveBeenCalledTimes(1)
    expect(api.list).toHaveBeenCalledWith('llu', 0)
    expect(router.currentRoute.value.query.q).toBe('llu')
  })

  it('clic en una canción reproduce con los resultados como cola', async () => {
    const lista = [cancion('s1', 'Granizo'), cancion('s2', 'Monzón')]
    api.list.mockResolvedValue({ items: lista, total: 2 })
    const { w } = await montar()
    await w.findAll('[data-prueba="reproducir"]')[1].trigger('click')
    expect(api.play).toHaveBeenCalledWith(lista[1], lista)
  })

  it('empty state message', async () => {
    api.list.mockResolvedValue({ items: [], total: 0 })
    const { w } = await montar('/catalogo?q=lluvia')
    expect(w.text()).toContain('No encontramos canciones con «lluvia».')
  })

  it('"Cargar más" pide la página siguiente con offset y la agrega', async () => {
    api.list.mockResolvedValueOnce({ items: [cancion('s1', 'Granizo')], total: 2 })
    const { w } = await montar()
    api.list.mockResolvedValueOnce({ items: [cancion('s2', 'Monzón')], total: 2 })
    await w.get('button.catalogo__mas').trigger('click')
    await flushPromises()
    expect(api.list).toHaveBeenLastCalledWith('', 1)
    expect(w.findAll('[data-prueba="reproducir"]')).toHaveLength(2)
    expect(w.find('button.catalogo__mas').exists()).toBe(false)
  })

  it('un error muestra el mensaje y "Reintentar" vuelve a pedir sin dejar resultados viejos', async () => {
    api.list.mockResolvedValueOnce({ items: [cancion('s1', 'Granizo')], total: 1 })
    const { w } = await montar()
    // Tras resetModules: la misma clase ApiError que importa la vista.
    const { ApiError } = await import('../../api/http')
    api.list.mockRejectedValueOnce(new ApiError(500, 'internal_error', 'Algo salió mal. Vuelve a intentarlo.'))
    await w.get('input[type="search"]').setValue('monzón')
    await vi.advanceTimersByTimeAsync(250)
    await flushPromises()
    expect(w.findAll('[data-prueba="reproducir"]')).toHaveLength(0)
    expect(w.text()).toContain('Algo salió mal. Vuelve a intentarlo.')

    api.list.mockResolvedValueOnce({ items: [cancion('s2', 'Monzón')], total: 1 })
    await w.findAll('button').find((b) => b.text() === 'Reintentar')!.trigger('click')
    await flushPromises()
    expect(api.list).toHaveBeenLastCalledWith('monzón', 0)
    expect(w.text()).toContain('Monzón')
  })

  it('follow button toggles aria-pressed', async () => {
    api.list.mockResolvedValue({ items: [cancion('s1', 'Granizo')], total: 1 })
    const { w } = await montar()
    const boton = () => w.get('button[data-prueba="seguir"]')
    expect(boton().attributes('aria-pressed')).toBe('false')
    expect(boton().text()).toBe('Seguir')
    api.follows.mockResolvedValue([
      { artist: 'Los Meteoros', followed_at: '2026-10-31T00:00:00Z', song_count: 1, cover_song_id: null },
    ])
    await boton().trigger('click')
    await flushPromises()
    expect(api.follow).toHaveBeenCalledWith('Los Meteoros')
    expect(boton().attributes('aria-pressed')).toBe('true')
    expect(boton().text()).toBe('Siguiendo')
  })
})
