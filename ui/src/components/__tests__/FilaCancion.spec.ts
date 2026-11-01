import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import type { SongOut } from '../../api/types'

vi.mock('../../composables/useFavoritos', () => ({
  useFavoritos: () => ({ esFavorita: () => false, alternar: vi.fn() }),
}))
vi.mock('../../composables/usePlayer', () => ({
  usePlayer: () => ({ enqueue: vi.fn(), playNext: vi.fn() }),
}))

import FilaCancion from '../FilaCancion.vue'

const cancion: SongOut = {
  id: 's1',
  title: 'Granizo',
  artist: 'Los Meteoros',
  album: 'Pronóstico',
  duration_seconds: 192,
  is_active: true,
  has_cover: false,
}

describe('FilaCancion', () => {
  it('muestra título, artista y duración m:ss y reproduce al hacer clic', async () => {
    const w = mount(FilaCancion, { props: { cancion } })
    expect(w.text()).toContain('Granizo')
    expect(w.text()).toContain('Los Meteoros')
    expect(w.text()).toContain('3:12')
    await w.get('[data-prueba="reproducir"]').trigger('click')
    expect(w.emitted('reproducir')).toHaveLength(1)
  })

  it('FilaCancion unavailable does not emit reproducir', async () => {
    const w = mount(FilaCancion, { props: { cancion, disponible: false } })
    expect(w.text()).toContain('No disponible')
    expect(w.get('[data-prueba="reproducir"]').attributes('disabled')).toBeDefined()
    await w.get('[data-prueba="reproducir"]').trigger('click')
    expect(w.emitted('reproducir')).toBeUndefined()
  })

  it('marca la fila que suena', () => {
    const w = mount(FilaCancion, { props: { cancion, sonando: true } })
    expect(w.get('[data-prueba="reproducir"]').attributes('aria-current')).toBe('true')
  })
})
