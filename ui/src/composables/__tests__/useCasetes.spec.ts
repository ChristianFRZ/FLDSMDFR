import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { PlaylistDetail, PlaylistSongOut, PlaylistSummary } from '../../api/types'

const list = vi.fn()
const create = vi.fn()
const get = vi.fn()
const rename = vi.fn()
const remove = vi.fn()
const addSong = vi.fn()
const removeSong = vi.fn()
const reorder = vi.fn()
const mostrar = vi.fn()

const resumen = (id: string, name: string): PlaylistSummary => ({
  id,
  name,
  song_count: 0,
  updated_at: '2026-10-30T00:00:00Z',
})

const fila = (songId: string, position: number): PlaylistSongOut => ({
  song_id: songId,
  title: `Canción ${songId}`,
  artist: 'Artista',
  album: 'Álbum',
  duration_seconds: 60,
  position,
  status: 'ok',
})

const detalle = (id: string, name: string, songIds: string[] = []): PlaylistDetail => ({
  id,
  name,
  songs: songIds.map((s, i) => fila(s, i)),
  total_seconds: songIds.length * 60,
})

// useCasetes es un singleton de módulo: cada prueba importa una copia nueva.
async function freshCasetes() {
  vi.resetModules()
  vi.doMock('../../api/playlists', () => ({
    list,
    create,
    get,
    rename,
    remove,
    addSong,
    removeSong,
    reorder,
  }))
  vi.doMock('../useAvisos', () => ({ useAvisos: () => ({ mostrar }) }))
  const { ApiError } = await import('../../api/http')
  const { useCasetes } = await import('../useCasetes')
  return { ApiError, casetes: useCasetes() }
}

describe('useCasetes', () => {
  beforeEach(() => {
    for (const fn of [list, create, get, rename, remove, addSong, removeSong, reorder, mostrar]) {
      fn.mockReset()
    }
  })

  it('cargar trae los casetes y selecciona el primero si no hay activo', async () => {
    const { casetes } = await freshCasetes()
    list.mockResolvedValue([resumen('p1', 'Tarde lluviosa'), resumen('p2', 'Correr')])
    get.mockResolvedValue(detalle('p1', 'Tarde lluviosa'))

    await casetes.cargar()

    expect(casetes.casetes.value.map((c) => c.id)).toEqual(['p1', 'p2'])
    expect(get).toHaveBeenCalledWith('p1')
    expect(casetes.activo.value?.id).toBe('p1')
  })

  it('cargar sin casetes deja el activo en null', async () => {
    const { casetes } = await freshCasetes()
    list.mockResolvedValue([])

    await casetes.cargar()

    expect(get).not.toHaveBeenCalled()
    expect(casetes.activo.value).toBeNull()
  })

  it('grabar sin casete activo avisa y no llama al API', async () => {
    const { casetes } = await freshCasetes()

    await casetes.grabar('s1')

    expect(mostrar).toHaveBeenCalledWith('Crea un casete primero.', expect.anything())
    expect(addSong).not.toHaveBeenCalled()
  })

  it('grabar una canción repetida avisa que ya está en el casete', async () => {
    const { ApiError, casetes } = await freshCasetes()
    list.mockResolvedValue([resumen('p1', 'Tarde lluviosa')])
    get.mockResolvedValue(detalle('p1', 'Tarde lluviosa', ['s1']))
    await casetes.cargar()
    addSong.mockRejectedValue(
      new ApiError(409, 'song_already_in_playlist', 'Esa canción ya está en el casete.'),
    )

    await casetes.grabar('s1')

    expect(addSong).toHaveBeenCalledWith('p1', 's1')
    expect(mostrar).toHaveBeenCalledWith('Esa canción ya está en este casete.', expect.anything())
  })

  it('grabar con éxito actualiza el casete activo y avisa con su nombre', async () => {
    const { casetes } = await freshCasetes()
    list.mockResolvedValue([resumen('p1', 'Tarde lluviosa')])
    get.mockResolvedValue(detalle('p1', 'Tarde lluviosa'))
    await casetes.cargar()
    addSong.mockResolvedValue(detalle('p1', 'Tarde lluviosa', ['s1']))

    await casetes.grabar('s1')

    expect(casetes.activo.value?.songs.map((s) => s.song_id)).toEqual(['s1'])
    expect(casetes.casetes.value[0].song_count).toBe(1)
    expect(mostrar).toHaveBeenCalledWith('Grabada en «Tarde lluviosa»', 'info')
  })

  it('mover(id, -1) pide reordenar con la canción intercambiada con la anterior', async () => {
    const { casetes } = await freshCasetes()
    list.mockResolvedValue([resumen('p1', 'Tarde lluviosa')])
    get.mockResolvedValue(detalle('p1', 'Tarde lluviosa', ['a', 'b', 'c']))
    await casetes.cargar()
    reorder.mockResolvedValue(detalle('p1', 'Tarde lluviosa', ['a', 'c', 'b']))

    await casetes.mover('c', -1)

    expect(reorder).toHaveBeenCalledWith('p1', ['a', 'c', 'b'])
    expect(casetes.activo.value?.songs.map((s) => s.song_id)).toEqual(['a', 'c', 'b'])
  })

  it('mover fuera de los extremos no llama al API', async () => {
    const { casetes } = await freshCasetes()
    list.mockResolvedValue([resumen('p1', 'Tarde lluviosa')])
    get.mockResolvedValue(detalle('p1', 'Tarde lluviosa', ['a', 'b']))
    await casetes.cargar()

    await casetes.mover('a', -1)
    await casetes.mover('b', 1)

    expect(reorder).not.toHaveBeenCalled()
  })

  it('crear agrega el casete y lo vuelve activo', async () => {
    const { casetes } = await freshCasetes()
    create.mockResolvedValue(resumen('p9', 'Correr'))
    get.mockResolvedValue(detalle('p9', 'Correr'))

    await casetes.crear('Correr')

    expect(create).toHaveBeenCalledWith('Correr')
    expect(casetes.casetes.value.map((c) => c.id)).toEqual(['p9'])
    expect(casetes.activo.value?.id).toBe('p9')
  })

  it('eliminar quita el casete activo y selecciona el siguiente disponible', async () => {
    const { casetes } = await freshCasetes()
    list.mockResolvedValue([resumen('p1', 'Tarde lluviosa'), resumen('p2', 'Correr')])
    get.mockResolvedValueOnce(detalle('p1', 'Tarde lluviosa'))
    await casetes.cargar()
    remove.mockResolvedValue(undefined)
    get.mockResolvedValueOnce(detalle('p2', 'Correr'))

    await casetes.eliminar()

    expect(remove).toHaveBeenCalledWith('p1')
    expect(casetes.casetes.value.map((c) => c.id)).toEqual(['p2'])
    expect(casetes.activo.value?.id).toBe('p2')
  })
})
