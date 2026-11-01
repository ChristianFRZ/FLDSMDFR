import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { NotificationOut } from '../../api/types'

const api = vi.hoisted(() => ({
  notifications: vi.fn(),
  markRead: vi.fn(),
  accept: vi.fn(),
  ignore: vi.fn(),
  cargarCasetes: vi.fn(),
  mostrar: vi.fn(),
}))
vi.mock('../../api/me', () => ({ notifications: api.notifications, markRead: api.markRead }))
vi.mock('../../api/invites', () => ({ accept: api.accept, ignore: api.ignore }))
vi.mock('../useCasetes', () => ({ useCasetes: () => ({ cargar: api.cargarCasetes }) }))
vi.mock('../useAvisos', () => ({ useAvisos: () => ({ mostrar: api.mostrar }) }))

const invitacion: NotificationOut = {
  id: 'invite:tok',
  type: 'invite',
  created_at: '2026-10-31T10:00:00Z',
  read: false,
  song: null,
  invite: { token: 'tok', playlist_id: 'p1', playlist_name: 'Viaje', inviter_name: 'Ana' },
}

let visibilidad: DocumentVisibilityState = 'visible'

async function cargarModulo() {
  vi.resetModules()
  return (await import('../useNotificaciones')).useNotificaciones()
}

describe('useNotificaciones', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    visibilidad = 'visible'
    vi.spyOn(document, 'visibilityState', 'get').mockImplementation(() => visibilidad)
    for (const f of Object.values(api)) f.mockReset()
    api.notifications.mockResolvedValue({ items: [invitacion], unread_count: 1 })
    api.markRead.mockResolvedValue(undefined)
    api.accept.mockResolvedValue({})
    api.cargarCasetes.mockResolvedValue(undefined)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('polls every 30s while visible', async () => {
    const n = await cargarModulo()
    n.iniciar()
    await vi.advanceTimersByTimeAsync(0)
    expect(api.notifications).toHaveBeenCalledTimes(1)
    expect(n.noLeidos.value).toBe(1)
    await vi.advanceTimersByTimeAsync(30_000)
    expect(api.notifications).toHaveBeenCalledTimes(2)
    n.detener()
    await vi.advanceTimersByTimeAsync(60_000)
    expect(api.notifications).toHaveBeenCalledTimes(2)
  })

  it('pauses when hidden and refreshes on visible', async () => {
    const n = await cargarModulo()
    n.iniciar()
    await vi.advanceTimersByTimeAsync(0)
    visibilidad = 'hidden'
    document.dispatchEvent(new Event('visibilitychange'))
    await vi.advanceTimersByTimeAsync(90_000)
    expect(api.notifications).toHaveBeenCalledTimes(1)
    visibilidad = 'visible'
    document.dispatchEvent(new Event('visibilitychange'))
    await vi.advanceTimersByTimeAsync(0)
    expect(api.notifications).toHaveBeenCalledTimes(2)
    n.detener()
  })

  it('network error is silent', async () => {
    api.notifications.mockRejectedValue(new TypeError('Failed to fetch'))
    const n = await cargarModulo()
    n.iniciar()
    await vi.advanceTimersByTimeAsync(30_000)
    expect(api.notifications).toHaveBeenCalledTimes(2)
    expect(api.mostrar).not.toHaveBeenCalled()
    n.detener()
  })

  it('accept removes card and reloads casetes', async () => {
    const n = await cargarModulo()
    n.iniciar()
    await vi.advanceTimersByTimeAsync(0)
    await n.aceptar('tok')
    expect(api.accept).toHaveBeenCalledWith('tok')
    expect(n.items.value).toEqual([])
    expect(api.cargarCasetes).toHaveBeenCalled()
    expect(api.mostrar).toHaveBeenCalledWith(expect.stringContaining('Viaje'))
    n.detener()
  })
})
