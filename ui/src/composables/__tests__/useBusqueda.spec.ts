import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useBusqueda, useOcupados } from '../useBusqueda'

function crear(consultar: (q: string) => Promise<string>) {
  const aplicar = vi.fn()
  const alFallar = vi.fn()
  const b = useBusqueda({ consultar, aplicar, alFallar, mensajeError: 'falló' })
  return { b, aplicar, alFallar }
}

describe('useBusqueda', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('busca una sola vez 250 ms después de dejar de escribir', async () => {
    const consultar = vi.fn().mockResolvedValue('r')
    const { b, aplicar } = crear(consultar)
    for (const t of ['l', 'll', ' lluvia ']) {
      b.busqueda.value = t
      b.alEscribir()
    }
    await vi.advanceTimersByTimeAsync(249)
    expect(consultar).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(1)
    expect(consultar).toHaveBeenCalledTimes(1)
    expect(consultar).toHaveBeenCalledWith('lluvia')
    expect(aplicar).toHaveBeenCalledWith('r')
    expect(b.buscado.value).toBe('lluvia')
    expect(b.cargando.value).toBe(false)
  })

  it('descarta la respuesta de una búsqueda obsoleta', async () => {
    const resolvers: Array<(v: string) => void> = []
    const consultar = vi.fn(() => new Promise<string>((res) => resolvers.push(res)))
    const { b, aplicar } = crear(consultar)
    const primera = b.buscar()
    const segunda = b.buscar()
    resolvers[1]('nueva')
    await segunda
    resolvers[0]('vieja')
    await primera
    expect(aplicar).toHaveBeenCalledTimes(1)
    expect(aplicar).toHaveBeenCalledWith('nueva')
  })

  it('un fallo vigente llama alFallar y deja el mensaje; uno obsoleto se ignora', async () => {
    const rechazos: Array<(e: Error) => void> = []
    const consultar = vi.fn(() => new Promise<string>((_, rej) => rechazos.push(rej)))
    const { b, alFallar } = crear(consultar)
    const primera = b.buscar()
    const segunda = b.buscar()
    rechazos[0](new Error('x'))
    await primera
    expect(alFallar).not.toHaveBeenCalled()
    rechazos[1](new Error('y'))
    await segunda
    expect(alFallar).toHaveBeenCalledTimes(1)
    expect(b.error.value).toBe('falló')
  })
})

describe('useOcupados', () => {
  it('marca y desmarca ids', () => {
    const { ocupados, marcar } = useOcupados()
    marcar('a', true)
    expect(ocupados.value.has('a')).toBe(true)
    marcar('a', false)
    expect(ocupados.value.has('a')).toBe(false)
  })
})
