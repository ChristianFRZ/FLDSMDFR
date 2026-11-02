import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { PlaylistDetail, PlaylistSummary } from '../../api/types'

const list = vi.fn()
const create = vi.fn()
const addSong = vi.fn()
const mostrar = vi.fn()

const resumen = (id: string, name: string, extra: Partial<PlaylistSummary> = {}): PlaylistSummary => ({
  id,
  name,
  song_count: 0,
  updated_at: '2026-10-30T00:00:00Z',
  has_cover: false,
  role: 'owner',
  ...extra,
})

const detalle = (id: string, name: string, n: number): PlaylistDetail => ({
  id,
  name,
  songs: Array.from({ length: n }, (_, i) => ({
    song_id: `s${i}`,
    title: `Canción ${i}`,
    artist: 'Artista',
    album: 'Álbum',
    duration_seconds: 60,
    position: i,
    status: 'ok',
  })),
  total_seconds: n * 60,
  has_cover: false,
  role: 'owner',
  members: [],
})

// useCasetes es un singleton de módulo: cada prueba importa una copia nueva.
async function freshCasetes() {
  vi.resetModules()
  vi.doMock('../../api/playlists', () => ({ list, create, addSong }))
  vi.doMock('../useAvisos', () => ({ useAvisos: () => ({ mostrar }) }))
  const { ApiError } = await import('../../api/http')
  const { useCasetes } = await import('../useCasetes')
  return { ApiError, casetes: useCasetes() }
}

describe('useCasetes', () => {
  beforeEach(() => {
    for (const fn of [list, create, addSong, mostrar]) fn.mockReset()
    localStorage.clear()
  })

  it('cargar trae los casetes', async () => {
    const { casetes } = await freshCasetes()
    list.mockResolvedValue([resumen('a', 'Viaje'), resumen('b', 'Lluvia')])
    await casetes.cargar()
    expect(casetes.casetes.value.map((c) => c.id)).toEqual(['a', 'b'])
    expect(casetes.error.value).toBe('')
  })

  it('crear agrega el casete al principio y lo devuelve', async () => {
    const { casetes } = await freshCasetes()
    list.mockResolvedValue([resumen('a', 'Viaje')])
    await casetes.cargar()
    create.mockResolvedValue(resumen('n', 'Nuevo'))
    const nuevo = await casetes.crear('Nuevo')
    expect(nuevo.id).toBe('n')
    expect(casetes.casetes.value.map((c) => c.id)).toEqual(['n', 'a'])
  })

  it('grabar actualiza el conteo, avisa y recuerda el destino', async () => {
    const { casetes } = await freshCasetes()
    list.mockResolvedValue([resumen('a', 'Viaje')])
    await casetes.cargar()
    addSong.mockResolvedValue(detalle('a', 'Viaje', 3))
    expect(await casetes.grabar('a', 's9')).toBe(true)
    expect(addSong).toHaveBeenCalledWith('a', 's9')
    expect(casetes.casetes.value[0].song_count).toBe(3)
    expect(mostrar).toHaveBeenCalledWith('Grabada en «Viaje»', 'info')
    expect(casetes.ultimoDestino.value).toBe('a')
    expect(localStorage.getItem('meloxo.ultimoCasete')).toBe('a')
  })

  it('grabar una canción repetida avisa con el nombre del casete', async () => {
    const { casetes, ApiError } = await freshCasetes()
    list.mockResolvedValue([resumen('a', 'Viaje')])
    await casetes.cargar()
    addSong.mockRejectedValue(new ApiError(409, 'song_already_in_playlist', 'ya está'))
    expect(await casetes.grabar('a', 's1')).toBe(false)
    expect(mostrar).toHaveBeenCalledWith('Esa canción ya está en «Viaje».', 'info')
  })

  it('el último destino sobrevive a recargar el módulo', async () => {
    localStorage.setItem('meloxo.ultimoCasete', 'b')
    const { casetes } = await freshCasetes()
    expect(casetes.ultimoDestino.value).toBe('b')
  })

  it('reiniciar vacía el estado, olvida el destino y descarta una carga en curso', async () => {
    const { casetes } = await freshCasetes()
    let resolver: (v: PlaylistSummary[]) => void = () => {}
    list.mockReturnValue(new Promise((r) => (resolver = r)))
    localStorage.setItem('meloxo.ultimoCasete', 'a')
    const carga = casetes.cargar()
    casetes.reiniciar()
    resolver([resumen('a', 'Viaje')])
    await carga
    expect(casetes.casetes.value).toEqual([])
    expect(casetes.ultimoDestino.value).toBeNull()
    expect(localStorage.getItem('meloxo.ultimoCasete')).toBeNull()
  })
})
