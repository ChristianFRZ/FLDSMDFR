import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { SongOut } from '../../api/types'

vi.mock('../../api/playbacks', () => ({ send: vi.fn(() => Promise.resolve({})) }))

import { usePlayer } from '../usePlayer'
import { useAvisos } from '../useAvisos'

const cancion = (id: string): SongOut => ({
  id,
  title: `Canción ${id}`,
  artist: 'Artista',
  album: 'Álbum',
  duration_seconds: 100,
  is_active: true,
})

function audioFalso() {
  const el = document.createElement('audio')
  el.play = vi.fn(() => Promise.resolve())
  el.pause = vi.fn()
  return el
}

describe('usePlayer', () => {
  const player = usePlayer()
  let el: HTMLAudioElement
  const [a, b, c] = [cancion('a'), cancion('b'), cancion('c')]

  beforeEach(() => {
    el = audioFalso()
    player.attach(el)
  })

  it('play asigna la URL de stream y marca la canción actual', async () => {
    await player.play(b, [a, b, c])
    expect(el.src).toContain('/api/songs/b/stream')
    expect(player.current.value?.id).toBe('b')
    expect(player.isPlaying.value).toBe(true)
  })

  it('ended avanza a la siguiente y al final se detiene', async () => {
    await player.play(b, [a, b, c])
    el.dispatchEvent(new Event('ended'))
    expect(player.current.value?.id).toBe('c')
    el.dispatchEvent(new Event('ended'))
    expect(player.current.value?.id).toBe('c')
    expect(player.isPlaying.value).toBe(false)
  })

  it('prev reinicia si ya pasaron más de 3 s y si no va a la anterior', async () => {
    await player.play(b, [a, b, c])
    player.currentTime.value = 10
    player.prev()
    expect(player.currentTime.value).toBe(0)
    expect(player.current.value?.id).toBe('b')
    player.prev()
    expect(player.current.value?.id).toBe('a')
  })

  it('error de audio muestra aviso y detiene', async () => {
    await player.play(a)
    el.dispatchEvent(new Event('error'))
    expect(player.isPlaying.value).toBe(false)
    expect(useAvisos().avisos.value.map((x) => x.texto)).toContain('No se pudo reproducir la canción.')
  })

  it('un fallo de carga con play() rechazado y evento error avisa una sola vez', async () => {
    const texto = 'No se pudo reproducir la canción.'
    const cuenta = () => useAvisos().avisos.value.filter((x) => x.texto === texto).length
    const antes = cuenta()
    Object.defineProperty(el, 'error', { value: { code: 4 } })
    el.play = vi.fn(() => {
      el.dispatchEvent(new Event('error'))
      return Promise.reject(new DOMException('no soportado', 'NotSupportedError'))
    })
    await player.play(a)
    expect(cuenta() - antes).toBe(1)
  })

  it('setVolume limita al rango 0..1 y llega al elemento', () => {
    player.setVolume(5)
    expect(el.volume).toBe(1)
    player.setVolume(0.4)
    expect(el.volume).toBe(0.4)
    expect(player.volume.value).toBe(0.4)
  })

  it('stop pausa, quita la fuente y vacía la canción y la cola', async () => {
    el.load = vi.fn()
    await player.play(b, [a, b, c])
    player.stop()
    expect(el.pause).toHaveBeenCalled()
    expect(el.hasAttribute('src')).toBe(false)
    expect(el.load).toHaveBeenCalled()
    expect(player.current.value).toBeNull()
    expect(player.queue.value).toEqual([])
    expect(player.isPlaying.value).toBe(false)
  })
})
