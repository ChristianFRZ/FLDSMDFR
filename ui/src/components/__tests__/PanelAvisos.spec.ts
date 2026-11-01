import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { NotificationOut } from '../../api/types'

const api = vi.hoisted(() => ({ notifications: vi.fn(), markRead: vi.fn() }))
vi.mock('../../api/me', () => ({ notifications: api.notifications, markRead: api.markRead }))
vi.mock('../../api/invites', () => ({ accept: vi.fn(), ignore: vi.fn() }))
vi.mock('../../composables/useCasetes', () => ({ useCasetes: () => ({ cargar: vi.fn() }) }))
vi.mock('../../composables/usePlayer', () => ({ usePlayer: () => ({ play: vi.fn() }) }))

const lanzamiento: NotificationOut = {
  id: 'release:s1',
  type: 'release',
  created_at: new Date(Date.now() - 2 * 3600_000).toISOString(),
  read: false,
  song: {
    id: 's1',
    title: 'Bésame',
    artist: 'Lila',
    album: 'Sencillo',
    duration_seconds: 200,
    is_active: true,
    has_cover: false,
  },
  invite: null,
}

describe('Campana y PanelAvisos', () => {
  beforeEach(() => {
    vi.resetModules()
    api.notifications.mockReset().mockResolvedValue({ items: [lanzamiento], unread_count: 1 })
    api.markRead.mockReset().mockResolvedValue(undefined)
  })

  it('opening bell marks visible as read', async () => {
    const { useNotificaciones } = await import('../../composables/useNotificaciones')
    const Campana = (await import('../Campana.vue')).default
    const n = useNotificaciones()
    await n.refrescar()
    const w = mount(Campana)
    expect(w.find('[data-prueba="contador"]').text()).toBe('1')
    await w.find('button[aria-haspopup="dialog"]').trigger('click')
    await flushPromises()
    expect(w.text()).toContain('NUEVO LANZAMIENTO')
    expect(w.text()).toContain('Lila · «Bésame»')
    expect(w.text()).toContain('hace 2 horas')
    expect(api.markRead).toHaveBeenCalledWith(['release:s1'])
    expect(w.find('[data-prueba="contador"]').exists()).toBe(false)
  })
})
