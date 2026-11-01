import { beforeEach, describe, expect, it, vi } from 'vitest'

const { like, unlike, favoriteIds, mostrar } = vi.hoisted(() => ({
  like: vi.fn(),
  unlike: vi.fn(),
  favoriteIds: vi.fn(),
  mostrar: vi.fn(),
}))
vi.mock('../../api/me', () => ({ like, unlike, favoriteIds }))
vi.mock('../useAvisos', () => ({ useAvisos: () => ({ mostrar }) }))

async function fresco() {
  vi.resetModules()
  return (await import('../useFavoritos')).useFavoritos()
}

describe('useFavoritos', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('cargar llena los ids', async () => {
    favoriteIds.mockResolvedValue(['a'])
    const f = await fresco()
    await f.cargar()
    expect(f.esFavorita('a')).toBe(true)
    expect(f.esFavorita('b')).toBe(false)
  })

  it('alternar marca al instante y sube la versión al confirmar', async () => {
    let resolver!: () => void
    like.mockReturnValue(new Promise<void>((r) => (resolver = r)))
    const f = await fresco()
    const promesa = f.alternar('a')
    expect(f.esFavorita('a')).toBe(true)
    resolver()
    await promesa
    expect(like).toHaveBeenCalledWith('a')
    expect(f.version.value).toBe(1)
  })

  it('si falla, revierte y avisa', async () => {
    favoriteIds.mockResolvedValue(['a'])
    unlike.mockRejectedValue(new Error('red'))
    const f = await fresco()
    await f.cargar()
    await f.alternar('a')
    expect(f.esFavorita('a')).toBe(true)
    expect(mostrar).toHaveBeenCalledWith(expect.stringContaining('favoritas'), 'error')
    expect(f.version.value).toBe(0)
  })
})
