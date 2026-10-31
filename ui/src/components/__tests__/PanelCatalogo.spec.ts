import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import type { PlaylistDetail, SongOut } from '../../api/types'

// vi.mock se eleva al inicio del archivo: los dobles se crean con vi.hoisted.
const { list, grabar, play } = vi.hoisted(() => ({ list: vi.fn(), grabar: vi.fn(), play: vi.fn() }))
const activo = ref<PlaylistDetail | null>({ id: 'p1', name: 'Tarde lluviosa', songs: [], total_seconds: 0 })
const current = ref(null)

vi.mock('../../api/songs', () => ({ list }))
vi.mock('../../composables/useCasetes', () => ({ useCasetes: () => ({ activo, grabar }) }))
vi.mock('../../composables/usePlayer', () => ({ usePlayer: () => ({ play, current }) }))

import PanelCatalogo from '../PanelCatalogo.vue'

const cancion = (id: string, title: string): SongOut => ({
  id,
  title,
  artist: 'Los Meteoros',
  album: 'Pronóstico',
  duration_seconds: 192,
  is_active: true,
})

describe('PanelCatalogo', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    list.mockReset()
    grabar.mockReset()
    play.mockReset()
    grabar.mockResolvedValue(undefined)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('busca una sola vez 250 ms después de dejar de escribir', async () => {
    list.mockResolvedValue({ items: [], total: 0 })
    const wrapper = mount(PanelCatalogo)
    await flushPromises()
    list.mockClear()

    const buscador = wrapper.get('input[aria-label="Buscar canción, artista o álbum"]')
    for (const parcial of ['l', 'll', 'llu', 'lluvia']) await buscador.setValue(parcial)
    await vi.advanceTimersByTimeAsync(249)
    expect(list).not.toHaveBeenCalled()

    await vi.advanceTimersByTimeAsync(1)
    expect(list).toHaveBeenCalledTimes(1)
    expect(list).toHaveBeenCalledWith('lluvia', 0)
  })

  it('el botón + graba la canción en el casete activo', async () => {
    list.mockResolvedValue({ items: [cancion('s1', 'Granizo')], total: 1 })
    const wrapper = mount(PanelCatalogo)
    await flushPromises()

    await wrapper.get('button[aria-label="Grabar «Granizo» en el casete"]').trigger('click')

    expect(grabar).toHaveBeenCalledWith('s1')
    expect(play).not.toHaveBeenCalled()
  })

  it('clic en la fila reproduce con la lista cargada como cola', async () => {
    const lista = [cancion('s1', 'Granizo'), cancion('s2', 'Monzón')]
    list.mockResolvedValue({ items: lista, total: 2 })
    const wrapper = mount(PanelCatalogo)
    await flushPromises()

    await wrapper.findAll('.catalogo__reproducir')[1].trigger('click')

    expect(play).toHaveBeenCalledWith(lista[1], lista)
  })

  it('una búsqueda sin resultados muestra el texto de vacío con la búsqueda', async () => {
    list.mockResolvedValue({ items: [], total: 0 })
    const wrapper = mount(PanelCatalogo)
    await flushPromises()

    await wrapper.get('input[type="search"]').setValue('lluvia')
    await vi.advanceTimersByTimeAsync(250)
    await flushPromises()

    expect(wrapper.text()).toContain('No encontramos canciones con «lluvia».')
  })

  it('"Cargar más" pide la página siguiente con offset y la agrega', async () => {
    list.mockResolvedValueOnce({ items: [cancion('s1', 'Granizo')], total: 2 })
    const wrapper = mount(PanelCatalogo)
    await flushPromises()
    list.mockResolvedValueOnce({ items: [cancion('s2', 'Monzón')], total: 2 })

    await wrapper.get('button.catalogo__mas').trigger('click')
    await flushPromises()

    expect(list).toHaveBeenLastCalledWith('', 1)
    expect(wrapper.findAll('.catalogo__reproducir')).toHaveLength(2)
    expect(wrapper.find('button.catalogo__mas').exists()).toBe(false)
  })

  it('un error muestra el mensaje y "Reintentar" vuelve a pedir', async () => {
    const { ApiError } = await import('../../api/http')
    list.mockRejectedValueOnce(new ApiError(0, 'network_error', 'No pudimos conectar con el servidor.'))
    const wrapper = mount(PanelCatalogo)
    await flushPromises()
    expect(wrapper.text()).toContain('No pudimos conectar con el servidor.')

    list.mockResolvedValueOnce({ items: [cancion('s1', 'Granizo')], total: 1 })
    const reintentar = wrapper.findAll('button').find((b) => b.text() === 'Reintentar')
    await reintentar!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Granizo')
  })
})
