import { beforeEach, describe, expect, it, vi } from 'vitest'

const oyente = { id: 'u1', name: 'Ana', email: 'ana@x.mx', role: 'listener' as const }
const admin = { ...oyente, id: 'u2', role: 'admin' as const }

const me = vi.fn()
const login = vi.fn()
const register = vi.fn()
const logout = vi.fn()
const push = vi.fn()

// El estado de sesión es un singleton de módulo: cada prueba importa una copia nueva.
async function freshSession() {
  vi.resetModules()
  vi.doMock('../../api/auth', () => ({ me, login, register, logout }))
  vi.doMock('../../router', () => ({ router: { push } }))
  const { ApiError } = await import('../../api/http')
  const { useSession } = await import('../useSession')
  return { ApiError, session: useSession() }
}

describe('useSession', () => {
  beforeEach(() => {
    for (const fn of [me, login, register, logout, push]) fn.mockReset()
  })

  it('load con me 401 deja user en null y ready en true', async () => {
    const { ApiError, session } = await freshSession()
    me.mockRejectedValue(new ApiError(401, 'not_authenticated', 'Entra primero.'))
    await session.load()
    expect(session.user.value).toBeNull()
    expect(session.ready.value).toBe(true)
  })

  it('load con sesión válida puebla user', async () => {
    const { session } = await freshSession()
    me.mockResolvedValue(oyente)
    await session.load()
    expect(session.user.value).toEqual(oyente)
    expect(session.ready.value).toBe(true)
  })

  it('load con fallo de red también marca ready', async () => {
    const { ApiError, session } = await freshSession()
    me.mockRejectedValue(new ApiError(0, 'network_error', 'Sin conexión.'))
    await session.load()
    expect(session.user.value).toBeNull()
    expect(session.ready.value).toBe(true)
  })

  it('login exitoso puebla user', async () => {
    const { session } = await freshSession()
    login.mockResolvedValue({ access_token: 't', token_type: 'bearer', user: oyente })
    await session.login('ana@x.mx', 'secreto123')
    expect(login).toHaveBeenCalledWith('ana@x.mx', 'secreto123')
    expect(session.user.value).toEqual(oyente)
  })

  it('login fallido propaga el error y no puebla user', async () => {
    const { ApiError, session } = await freshSession()
    login.mockRejectedValue(new ApiError(401, 'invalid_credentials', 'Credenciales incorrectas.'))
    await expect(session.login('a@x.mx', 'mala')).rejects.toMatchObject({ code: 'invalid_credentials' })
    expect(session.user.value).toBeNull()
  })

  it('register exitoso puebla user', async () => {
    const { session } = await freshSession()
    register.mockResolvedValue({ access_token: 't', token_type: 'bearer', user: oyente })
    await session.register('Ana', 'ana@x.mx', 'secreto123')
    expect(register).toHaveBeenCalledWith('Ana', 'ana@x.mx', 'secreto123')
    expect(session.user.value).toEqual(oyente)
  })

  it('isAdmin depende del rol', async () => {
    const { session } = await freshSession()
    me.mockResolvedValue(oyente)
    await session.load()
    expect(session.isAdmin.value).toBe(false)
    me.mockResolvedValue(admin)
    await session.load()
    expect(session.isAdmin.value).toBe(true)
  })

  it('logout limpia user aunque el servidor falle', async () => {
    const { session } = await freshSession()
    me.mockResolvedValue(oyente)
    await session.load()
    logout.mockRejectedValue(new Error('red'))
    await session.logout()
    expect(session.user.value).toBeNull()
    expect(push).toHaveBeenCalledWith('/acceso')
  })

  it('un 401 en cualquier petición limpia user y navega a /acceso', async () => {
    const { session } = await freshSession()
    me.mockResolvedValue(oyente)
    await session.load()
    const fetchMock = vi.fn().mockResolvedValue(new Response('{}', { status: 401 }))
    vi.stubGlobal('fetch', fetchMock)
    const { request } = await import('../../api/http')
    await request('/api/playlists').catch(() => undefined)
    expect(session.user.value).toBeNull()
    expect(push).toHaveBeenCalledWith('/acceso')
    vi.unstubAllGlobals()
  })
})
