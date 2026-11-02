import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { PlaylistSummary } from '../../api/types'

const api = vi.hoisted(() => ({ list: vi.fn(), create: vi.fn(), addSong: vi.fn(), mostrar: vi.fn() }))
vi.mock('../../api/playlists', () => ({ list: api.list, create: api.create, addSong: api.addSong }))
vi.mock('../../composables/useAvisos', () => ({ useAvisos: () => ({ mostrar: api.mostrar }) }))

const resumen = (id: string, name: string): PlaylistSummary => ({
  id,
  name,
  song_count: 1,
  updated_at: '2026-10-30T00:00:00Z',
  has_cover: false,
  role: 'owner',
})

async function montar() {
  vi.resetModules()
  const { useCasetes } = await import('../../composables/useCasetes')
  const SelectorGrabar = (await import('../SelectorGrabar.vue')).default
  await useCasetes().cargar()
  const w = mount(SelectorGrabar, { props: { songId: 's1', titulo: 'Granizo' }, attachTo: document.body })
  await w.get('button[aria-label="Grabar «Granizo» en un casete"]').trigger('click')
  return w
}

describe('SelectorGrabar', () => {
  beforeEach(() => {
    for (const f of Object.values(api)) f.mockReset()
    localStorage.clear()
    api.list.mockResolvedValue([resumen('a', 'Viaje'), resumen('b', 'Lluvia')])
  })

  it('selector lists writable casetes with last destination first', async () => {
    localStorage.setItem('meloxo.ultimoCasete', 'b')
    const w = await montar()
    const opciones = w.findAll('[data-prueba="destino"]')
    expect(opciones.map((o) => o.text())).toEqual([
      expect.stringContaining('Lluvia'),
      expect.stringContaining('Viaje'),
    ])
    expect(opciones[0].text()).toContain('Último usado')
    w.unmount()
  })

  it('duplicate shows friendly message', async () => {
    const w = await montar()
    // Tras resetModules: la misma clase ApiError que usa useCasetes.
    const { ApiError } = await import('../../api/http')
    api.addSong.mockRejectedValue(new ApiError(409, 'song_already_in_playlist', 'x'))
    await w.findAll('[data-prueba="destino"]')[0].trigger('click')
    await flushPromises()
    expect(api.mostrar).toHaveBeenCalledWith('Esa canción ya está en «Viaje».', 'info')
    expect(w.emitted('grabado')).toBeUndefined()
    w.unmount()
  })

  it('nuevo casete en línea crea y graba en él', async () => {
    api.create.mockResolvedValue(resumen('n', 'Fiesta'))
    api.addSong.mockResolvedValue({ id: 'n', name: 'Fiesta', songs: [], total_seconds: 0, has_cover: false, role: 'owner', members: [] })
    const w = await montar()
    await w.get('button[data-prueba="nuevo-casete"]').trigger('click')
    const campo = w.get('input[aria-label="Nombre del casete nuevo"]')
    await campo.setValue('Fiesta')
    await campo.trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(api.create).toHaveBeenCalledWith('Fiesta')
    expect(api.addSong).toHaveBeenCalledWith('n', 's1')
    expect(w.emitted('grabado')).toEqual([['n']])
    w.unmount()
  })
})
