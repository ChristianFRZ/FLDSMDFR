import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { computed, ref } from 'vue'
import type { SongOut } from '../../api/types'

const cancion = (id: string): SongOut => ({
  id,
  title: `Canción ${id}`,
  artist: 'Artista',
  album: 'Álbum',
  duration_seconds: 100,
  is_active: true,
  has_cover: false,
})

const estado = vi.hoisted(() => ({ jugador: null as unknown as Record<string, unknown> }))
vi.mock('../../composables/usePlayer', () => ({ usePlayer: () => estado.jugador }))
vi.mock('../../composables/useFavoritos', () => ({
  useFavoritos: () => ({ esFavorita: () => false, alternar: vi.fn(), cargar: vi.fn() }),
}))

import Reproductor from '../Reproductor.vue'

describe('Reproductor', () => {
  const siguientes = ref<SongOut[]>([])

  beforeEach(() => {
    siguientes.value = [cancion('b'), cancion('c')]
    estado.jugador = {
      current: ref(cancion('a')),
      queue: ref([]),
      isPlaying: ref(false),
      currentTime: ref(0),
      duration: ref(100),
      buffered: ref([]),
      volume: ref(1),
      shuffle: ref(false),
      repeat: ref('off'),
      upcoming: computed(() => siguientes.value),
      toggle: vi.fn(),
      next: vi.fn(),
      prev: vi.fn(),
      seek: vi.fn(),
      setVolume: vi.fn(),
      toggleShuffle: vi.fn(),
      cycleRepeat: vi.fn(),
      removeFromQueue: vi.fn((i: number) => siguientes.value.splice(i, 1)),
      moveInQueue: vi.fn(),
    }
  })

  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('letras y dispositivos están deshabilitados con Próximamente', () => {
    const w = mount(Reproductor)
    for (const etiqueta of ['Letras', 'Dispositivos']) {
      const boton = w.find(`[aria-label^="${etiqueta}"]`)
      expect(boton.attributes('aria-disabled')).toBe('true')
      expect(boton.attributes('title')).toBe('Próximamente')
    }
  })

  it('el botón repetir refleja el modo', async () => {
    const w = mount(Reproductor)
    expect(w.find('[data-prueba="repetir"]').attributes('aria-label')).toBe('Repetir: apagado')
    ;(estado.jugador.repeat as { value: string }).value = 'one'
    await w.vm.$nextTick()
    const boton = w.find('[data-prueba="repetir"]')
    expect(boton.attributes('aria-label')).toBe('Repetir: esta canción')
    expect(boton.attributes('aria-pressed')).toBe('true')
  })

  it('el panel de cola lista lo que sigue y permite quitar', async () => {
    const w = mount(Reproductor, { attachTo: document.body })
    await w.find('[aria-label="Cola de reproducción"]').trigger('click')
    const filas = w.findAll('[data-prueba="fila-cola"]')
    expect(filas.map((f) => f.text())).toEqual([
      expect.stringContaining('Canción b'),
      expect.stringContaining('Canción c'),
    ])
    await w.find('[aria-label="Quitar «Canción b» de la cola"]').trigger('click')
    expect(estado.jugador.removeFromQueue).toHaveBeenCalledWith(0)
    w.unmount()
  })

  it('la barra espaciadora reproduce salvo si escribes', async () => {
    const w = mount(Reproductor, { attachTo: document.body })
    document.body.dispatchEvent(new KeyboardEvent('keydown', { key: ' ', bubbles: true }))
    expect(estado.jugador.toggle).toHaveBeenCalledTimes(1)
    const input = document.createElement('input')
    document.body.appendChild(input)
    input.dispatchEvent(new KeyboardEvent('keydown', { key: ' ', bubbles: true }))
    expect(estado.jugador.toggle).toHaveBeenCalledTimes(1)
    w.unmount()
  })
})
