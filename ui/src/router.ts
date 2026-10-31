import { createRouter, createWebHistory } from 'vue-router'
import { useSession } from './composables/useSession'

// Las vistas se cargan bajo demanda.
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/acceso',
      name: 'acceso',
      component: () => import('./views/AccesoView.vue'),
    },
    {
      path: '/',
      name: 'casetera',
      component: () => import('./views/CaseteraView.vue'),
      meta: { auth: true, encabezadoPropio: true },
    },
    {
      path: '/cabina',
      name: 'cabina',
      component: () => import('./views/CabinaView.vue'),
      meta: { auth: true, admin: true },
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

// useSession importa este router (para navegar tras un 401) y el guard usa useSession:
// el ciclo es seguro porque ambos solo se usan dentro de funciones, nunca al evaluar el módulo.
let sesionCargada: Promise<void> | null = null

router.beforeEach(async (to) => {
  const session = useSession()
  sesionCargada ??= session.load()
  await sesionCargada

  if (to.meta.auth && !session.user.value) return { name: 'acceso' }
  if (to.meta.admin && !session.isAdmin.value) return { name: 'casetera' }
  if (to.name === 'acceso' && session.user.value) return { name: 'casetera' }
})
