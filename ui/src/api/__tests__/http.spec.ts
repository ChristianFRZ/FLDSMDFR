import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ApiError } from '../http'

// Espera a que la promesa falle y devuelve el error con su tipo.
async function fallo(promesa: Promise<unknown>): Promise<ApiError> {
  try {
    await promesa
  } catch (error) {
    return error as ApiError
  }
  throw new Error('La promesa debía fallar')
}

function respuesta(status: number, cuerpo?: unknown): Response {
  return new Response(cuerpo === undefined ? null : JSON.stringify(cuerpo), {
    status,
    headers: cuerpo === undefined ? {} : { 'Content-Type': 'application/json' },
  })
}

// El handler de 401 es estado de módulo: cada prueba importa una copia nueva.
async function freshHttp() {
  vi.resetModules()
  return await import('../http')
}

describe('http.request', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('200 con JSON devuelve el objeto y usa credentials same-origin', async () => {
    fetchMock.mockResolvedValue(respuesta(200, { id: 'u1' }))
    const { request } = await freshHttp()
    await expect(request('/api/auth/me')).resolves.toEqual({ id: 'u1' })
    expect(fetchMock.mock.calls[0][1].credentials).toBe('same-origin')
  })

  it('serializa json con Content-Type y método', async () => {
    fetchMock.mockResolvedValue(respuesta(200, {}))
    const { request } = await freshHttp()
    await request('/api/x', { method: 'POST', json: { a: 1 } })
    const init = fetchMock.mock.calls[0][1]
    expect(init.body).toBe('{"a":1}')
    expect(new Headers(init.headers).get('Content-Type')).toBe('application/json')
  })

  it('no fija Content-Type cuando el cuerpo es FormData', async () => {
    fetchMock.mockResolvedValue(respuesta(201, {}))
    const { request } = await freshHttp()
    await request('/api/songs', { method: 'POST', body: new FormData() })
    expect(new Headers(fetchMock.mock.calls[0][1].headers).has('Content-Type')).toBe(false)
  })

  it('204 devuelve undefined', async () => {
    fetchMock.mockResolvedValue(respuesta(204))
    const { request } = await freshHttp()
    await expect(request('/api/auth/logout', { method: 'POST' })).resolves.toBeUndefined()
  })

  it('409 lanza ApiError con code, status y mensaje del cuerpo', async () => {
    fetchMock.mockResolvedValue(
      respuesta(409, { error: { code: 'email_taken', message: 'Ese correo ya está registrado.' } }),
    )
    const { request, ApiError } = await freshHttp()
    const error = await fallo(request('/api/auth/register', { method: 'POST' }))
    expect(error).toBeInstanceOf(ApiError)
    expect(error.code).toBe('email_taken')
    expect(error.status).toBe(409)
    expect(error.message).toBe('Ese correo ya está registrado.')
  })

  it('error sin cuerpo JSON válido usa un código genérico', async () => {
    fetchMock.mockResolvedValue(new Response('<html>', { status: 502 }))
    const { request } = await freshHttp()
    const error = await fallo(request('/api/x'))
    expect(error.status).toBe(502)
    expect(error.code).toBe('unknown_error')
  })

  it('401 en una ruta protegida invoca onUnauthorized', async () => {
    fetchMock.mockResolvedValue(
      respuesta(401, { error: { code: 'not_authenticated', message: 'Entra primero.' } }),
    )
    const { request, onUnauthorized } = await freshHttp()
    const handler = vi.fn()
    onUnauthorized(handler)
    await expect(request('/api/playlists')).rejects.toMatchObject({ status: 401 })
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('401 en /api/auth/login no invoca onUnauthorized', async () => {
    fetchMock.mockResolvedValue(
      respuesta(401, { error: { code: 'invalid_credentials', message: 'Credenciales incorrectas.' } }),
    )
    const { request, onUnauthorized } = await freshHttp()
    const handler = vi.fn()
    onUnauthorized(handler)
    await expect(request('/api/auth/login', { method: 'POST' })).rejects.toMatchObject({
      code: 'invalid_credentials',
    })
    expect(handler).not.toHaveBeenCalled()
  })

  it('fetch rechazado lanza ApiError network_error', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))
    const { request, ApiError } = await freshHttp()
    const error = await fallo(request('/api/x'))
    expect(error).toBeInstanceOf(ApiError)
    expect(error.code).toBe('network_error')
    expect(error.status).toBe(0)
  })
})
