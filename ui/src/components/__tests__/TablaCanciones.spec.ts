import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { SongOut } from '../../api/types'

const api = vi.hoisted(() => ({ list: vi.fn(), uploadCover: vi.fn(), mostrar: vi.fn() }))
vi.mock('../../api/songs', () => ({
  list: api.list,
  uploadCover: api.uploadCover,
  coverUrl: (id: string) => `/api/songs/${id}/cover`,
}))
vi.mock('../../composables/useAvisos', () => ({ useAvisos: () => ({ mostrar: api.mostrar }) }))

import TablaCanciones from '../TablaCanciones.vue'

const cancion: SongOut = {
  id: 's1',
  title: 'Granizo',
  artist: 'Los Meteoros',
  album: 'Pronóstico',
  duration_seconds: 12,
  is_active: true,
  has_cover: false,
}

describe('TablaCanciones', () => {
  beforeEach(() => {
    for (const f of Object.values(api)) f.mockReset()
    api.list.mockResolvedValue({ items: [cancion], total: 1 })
  })

  it('cambiar portada sube la imagen y muestra la miniatura', async () => {
    api.uploadCover.mockResolvedValue({ ...cancion, has_cover: true })
    const w = mount(TablaCanciones)
    await flushPromises()
    expect(w.find('img').exists()).toBe(false)

    const imagen = new File([new Uint8Array(10)], 'p.png', { type: 'image/png' })
    const campo = w.get('input[aria-label="Cambiar portada de «Granizo»"]')
    Object.defineProperty(campo.element, 'files', { value: [imagen], configurable: true })
    await campo.trigger('change')
    await flushPromises()

    expect(api.uploadCover).toHaveBeenCalledWith('s1', imagen)
    expect(w.get('img').attributes('src')).toMatch(/^\/api\/songs\/s1\/cover\?v=\d+$/)
  })
})
