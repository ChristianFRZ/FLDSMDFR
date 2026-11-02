import { describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'

const user = ref<null | { name: string }>(null)
vi.mock('../composables/useSession', () => ({
  useSession: () => ({ user, isAdmin: ref(false), load: () => Promise.resolve() }),
}))
vi.mock('../composables/useAvisos', () => ({ useAvisos: () => ({ mostrar: vi.fn() }) }))

import { router } from '../router'
import { destinoSeguro } from '../composables/destino'

describe('router', () => {
  it('sin sesión manda a acceso con la ruta pedida en siguiente', async () => {
    await router.push('/invitacion/abc123')
    expect(router.currentRoute.value.name).toBe('acceso')
    expect(router.currentRoute.value.query.siguiente).toBe('/invitacion/abc123')
  })
})

describe('destinoSeguro', () => {
  it('acepta rutas internas', () => {
    expect(destinoSeguro('/casete/1')).toBe('/casete/1')
    expect(destinoSeguro('/invitacion/abc?x=1')).toBe('/invitacion/abc?x=1')
  })

  it('ignora destinos externos o inválidos', () => {
    expect(destinoSeguro('//evil.com')).toBe('/')
    expect(destinoSeguro('/\\evil.com')).toBe('/')
    expect(destinoSeguro('https://evil.com')).toBe('/')
    expect(destinoSeguro(undefined)).toBe('/')
    expect(destinoSeguro(['/a'])).toBe('/')
    expect(destinoSeguro('/acceso')).toBe('/')
  })
})
