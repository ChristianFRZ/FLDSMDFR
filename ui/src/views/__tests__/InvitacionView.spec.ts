import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

const api = vi.hoisted(() => ({ claim: vi.fn(), mostrar: vi.fn(), refrescar: vi.fn(), abrir: vi.fn() }))
vi.mock('../../api/invites', () => ({ claim: api.claim }))
vi.mock('../../composables/useAvisos', () => ({ useAvisos: () => ({ mostrar: api.mostrar }) }))
vi.mock('../../composables/useNotificaciones', () => ({
  useNotificaciones: () => ({ refrescar: api.refrescar, abrirPanel: api.abrir }),
}))

async function montar() {
  vi.resetModules()
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<p />' } },
      { path: '/casete/:id', component: { template: '<p />' } },
      { path: '/invitacion/:token', component: { template: '<p />' } },
    ],
  })
  await router.push('/invitacion/tok')
  const InvitacionView = (await import('../InvitacionView.vue')).default
  const { ApiError } = await import('../../api/http')
  return { router, ApiError, InvitacionView }
}

describe('InvitacionView', () => {
  beforeEach(() => {
    for (const f of Object.values(api)) f.mockReset()
    api.refrescar.mockResolvedValue(undefined)
  })

  it('una invitación nueva lleva a Inicio y abre los avisos', async () => {
    const { router, InvitacionView } = await montar()
    api.claim.mockResolvedValue({ playlist_id: 'p1', playlist_name: 'Viaje', status: 'pending' })
    mount(InvitacionView, { global: { plugins: [router] } })
    await flushPromises()
    expect(api.claim).toHaveBeenCalledWith('tok')
    expect(router.currentRoute.value.fullPath).toBe('/')
    expect(api.refrescar).toHaveBeenCalled()
    expect(api.abrir).toHaveBeenCalled()
  })

  it('invitation already_member navigates to casete', async () => {
    const { router, InvitacionView } = await montar()
    api.claim.mockResolvedValue({ playlist_id: 'p1', playlist_name: 'Viaje', status: 'member' })
    mount(InvitacionView, { global: { plugins: [router] } })
    await flushPromises()
    expect(api.mostrar).toHaveBeenCalledWith('Ya formas parte de este casete.', 'info')
    expect(router.currentRoute.value.fullPath).toBe('/casete/p1')
  })

  it('invalid invitation shows message', async () => {
    const { router, ApiError, InvitacionView } = await montar()
    api.claim.mockRejectedValue(new ApiError(404, 'invite_not_found', 'x'))
    mount(InvitacionView, { global: { plugins: [router] } })
    await flushPromises()
    expect(api.mostrar).toHaveBeenCalledWith('Este enlace ya no es válido.', 'error')
    expect(router.currentRoute.value.fullPath).toBe('/')
  })
})
