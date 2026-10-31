import { computed, readonly, ref, type ComputedRef, type Ref } from 'vue'
import * as auth from '../api/auth'
import { onUnauthorized } from '../api/http'
import type { UserOut } from '../api/types'
import { router } from '../router'
import { useAvisos } from './useAvisos'

// Estado singleton a nivel de módulo. El token vive en una cookie httpOnly: el cliente nunca lo toca.
const user = ref<UserOut | null>(null)
const ready = ref(false)
const isAdmin = computed(() => user.value?.role === 'admin')

// Un 401 con sesión abierta significa que expiró: se limpia y se manda a entrar de nuevo.
// Sin usuario (p. ej. el 401 inicial de /auth/me) no hay nada que cerrar.
onUnauthorized(() => {
  if (user.value === null) return
  user.value = null
  useAvisos().mostrar('Tu sesión terminó. Entra de nuevo para seguir escuchando.', 'error')
  void router.push('/acceso')
})

async function load(): Promise<void> {
  try {
    user.value = await auth.me()
  } catch {
    // 401 = sin sesión; un fallo de red también deja al usuario fuera hasta que pueda entrar.
    user.value = null
  } finally {
    ready.value = true
  }
}

async function login(email: string, password: string): Promise<void> {
  user.value = (await auth.login(email, password)).user
}

async function register(name: string, email: string, password: string): Promise<void> {
  user.value = (await auth.register(name, email, password)).user
}

async function logout(): Promise<void> {
  try {
    await auth.logout()
  } catch {
    // Si el servidor no responde igual se cierra la sesión local; la cookie expira sola.
  }
  user.value = null
  await router.push('/acceso')
}

export function useSession(): {
  user: Readonly<Ref<UserOut | null>>
  isAdmin: ComputedRef<boolean>
  ready: Ref<boolean>
  load: () => Promise<void>
  login: (email: string, password: string) => Promise<void>
  register: (name: string, email: string, password: string) => Promise<void>
  logout: () => Promise<void>
} {
  return { user: readonly(user), isAdmin, ready, load, login, register, logout }
}
