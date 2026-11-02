import { mount, flushPromises } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

const user = ref({ id: 'u1', name: 'Alex López', email: 'a@b.mx', role: 'listener' })
const isAdmin = ref(false)
vi.mock('../../composables/useSession', () => ({
  useSession: () => ({ user, isAdmin, logout: vi.fn() }),
}))

import EncabezadoSuperior from '../EncabezadoSuperior.vue'

function montar() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'inicio', component: { template: '<div />' } },
      { path: '/catalogo', name: 'catalogo', component: { template: '<div />' } },
    ],
  })
  const wrapper = mount(EncabezadoSuperior, {
    global: { plugins: [router], stubs: { Campana: true } },
    attachTo: document.body,
  })
  return { wrapper, router }
}

describe('EncabezadoSuperior', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('Ctrl+K enfoca la búsqueda', async () => {
    const { wrapper } = montar()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true }))
    expect(document.activeElement).toBe(wrapper.find('input[type="search"]').element)
    wrapper.unmount()
  })

  it('⌘K enfoca la búsqueda', async () => {
    const { wrapper } = montar()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'K', metaKey: true }))
    expect(document.activeElement).toBe(wrapper.find('input[type="search"]').element)
    wrapper.unmount()
  })

  it('Enter lleva al catálogo con la consulta', async () => {
    const { wrapper, router } = montar()
    const input = wrapper.find('input[type="search"]')
    await input.setValue('  Natalia ')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('catalogo')
    expect(router.currentRoute.value.query.q).toBe('Natalia')
    wrapper.unmount()
  })

  it('muestra el rol y las iniciales', () => {
    const { wrapper } = montar()
    expect(wrapper.text()).toContain('Oyente')
    expect(wrapper.text()).toContain('AL')
    isAdmin.value = true
    wrapper.unmount()
  })

  it('Plus aparece deshabilitado con Próximamente', () => {
    const { wrapper } = montar()
    const plus = wrapper.find('[data-prueba="plus"]')
    expect(plus.attributes('aria-disabled')).toBe('true')
    expect(plus.attributes('title')).toBe('Próximamente')
    wrapper.unmount()
  })
})
