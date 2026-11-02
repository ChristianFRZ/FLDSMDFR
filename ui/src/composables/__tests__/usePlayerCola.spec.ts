import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { SongOut } from '../../api/types'

vi.mock('../../api/playbacks', () => ({ send: vi.fn(() => Promise.resolve({})) }))

const cancion = (id: string): SongOut => ({
  id,
  title: `Canción ${id}`,
  artist: 'Artista',
  album: 'Álbum',
  duration_seconds: 100,
  is_active: true,
  has_cover: false,
})
const [a, b, c, d, e] = ['a', 'b', 'c', 'd', 'e'].map(cancion)

// El reproductor es un singleton: cada prueba importa una copia nueva y un <audio> falso.
async function nuevoReproductor() {
  vi.resetModules()
  const { usePlayer } = await import('../usePlayer')
  const player = usePlayer()
  const el = document.createElement('audio')
  el.play = vi.fn(() => Promise.resolve())
  el.pause = vi.fn()
  player.attach(el)
  return { player, el }
}

const ids = (songs: SongOut[]) => songs.map((s) => s.id)

describe('usePlayer · cola, aleatorio y repetir', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('repeat one reinicia al terminar pero siguiente avanza', async () => {
    const { player, el } = await nuevoReproductor()
    await player.play(a, [a, b])
    player.cycleRepeat()
    player.cycleRepeat()
    expect(player.repeat.value).toBe('one')
    player.currentTime.value = 50
    el.dispatchEvent(new Event('ended'))
    expect(player.current.value?.id).toBe('a')
    expect(el.currentTime).toBe(0)
    expect(el.play).toHaveBeenCalledTimes(2)
    player.next()
    expect(player.current.value?.id).toBe('b')
  })

  it('repeat all vuelve al inicio al acabar la cola', async () => {
    const { player, el } = await nuevoReproductor()
    await player.play(b, [a, b])
    player.cycleRepeat()
    expect(player.repeat.value).toBe('all')
    el.dispatchEvent(new Event('ended'))
    expect(player.current.value?.id).toBe('a')
  })

  it('aleatorio con una sola canción se detiene al terminar', async () => {
    const { player, el } = await nuevoReproductor()
    player.toggleShuffle()
    await player.play(a, [a])
    el.dispatchEvent(new Event('ended'))
    expect(player.current.value?.id).toBe('a')
    expect(player.isPlaying.value).toBe(false)
    expect(el.play).toHaveBeenCalledTimes(1)
  })

  it('aleatorio recorre cada canción exactamente una vez', async () => {
    const { player, el } = await nuevoReproductor()
    player.toggleShuffle()
    await player.play(c, [a, b, c, d, e])
    const vistas = [player.current.value!.id]
    for (let i = 0; i < 10 && player.isPlaying.value; i++) {
      el.dispatchEvent(new Event('ended'))
      if (player.isPlaying.value) vistas.push(player.current.value!.id)
    }
    expect(vistas[0]).toBe('c')
    expect([...vistas].sort()).toEqual(['a', 'b', 'c', 'd', 'e'])
  })

  it('desactivar aleatorio vuelve al orden original desde la canción actual', async () => {
    const { player } = await nuevoReproductor()
    player.toggleShuffle()
    await player.play(b, [a, b, c, d])
    player.toggleShuffle()
    expect(ids(player.upcoming.value)).toEqual(['c', 'd'])
  })

  it('enqueue, playNext, removeFromQueue y moveInQueue editan lo que sigue', async () => {
    const { player } = await nuevoReproductor()
    await player.play(a, [a, b])
    player.enqueue(c)
    player.playNext(d)
    expect(ids(player.upcoming.value)).toEqual(['d', 'b', 'c'])
    player.moveInQueue(2, 0)
    expect(ids(player.upcoming.value)).toEqual(['c', 'd', 'b'])
    player.removeFromQueue(1)
    expect(ids(player.upcoming.value)).toEqual(['c', 'b'])
    player.next()
    expect(player.current.value?.id).toBe('c')
  })

  it('enqueue sin canción sonando empieza a reproducir', async () => {
    const { player } = await nuevoReproductor()
    player.enqueue(a)
    await Promise.resolve()
    expect(player.current.value?.id).toBe('a')
  })

  it('recuerda aleatorio y repetir en localStorage', async () => {
    let { player } = await nuevoReproductor()
    player.toggleShuffle()
    player.cycleRepeat()
    expect(localStorage.getItem('meloxo.shuffle')).toBe('1')
    expect(localStorage.getItem('meloxo.repeat')).toBe('all')
    ;({ player } = await nuevoReproductor())
    expect(player.shuffle.value).toBe(true)
    expect(player.repeat.value).toBe('all')
  })

  it('si localStorage lanza, el reproductor sigue funcionando', async () => {
    const roto = {
      getItem: () => {
        throw new Error('bloqueado')
      },
      setItem: () => {
        throw new Error('bloqueado')
      },
    }
    vi.stubGlobal('localStorage', roto)
    const { player } = await nuevoReproductor()
    expect(player.shuffle.value).toBe(false)
    expect(() => player.toggleShuffle()).not.toThrow()
    expect(player.shuffle.value).toBe(true)
  })
})
