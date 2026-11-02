import { createRouter, createWebHistory } from 'vue-router'
import { useAvisos } from './composables/useAvisos'
import { useSession } from './composables/useSession'

// Las vistas se cargan bajo demanda.
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/acceso',
      name: 'acceso',
      component: () => import('./views/AccesoView.vue'),
      meta: { sinLayout: true },
    },
    {
      path: '/',
      name: 'inicio',
      component: () => import('./views/InicioView.vue'),
      meta: { auth: true },
    },
    {
      path: '/catalogo',
      name: 'catalogo',
      component: () => import('./views/CatalogoView.vue'),
      meta: { auth: true },
    },
    {
      path: '/streaming',
      name: 'streaming',
      component: () => import('./views/StreamingView.vue'),
      meta: { auth: true },
    },
    {
      path: '/casete/:id',
      name: 'casete',
      component: () => import('./views/CaseteView.vue'),
      meta: { auth: true },
    },
    {
      path: '/favoritas',
      name: 'favoritas',
      component: () => import('./views/FavoritasView.vue'),
      meta: { auth: true },
    },
    {
      path: '/historial',
      name: 'historial',
      component: () => import('./views/HistorialView.vue'),
      meta: { auth: true },
    },
    {
      path: '/biblioteca',
      name: 'biblioteca',
      component: () => import('./views/BibliotecaView.vue'),
      meta: { auth: true },
    },
    {
      path: '/invitacion/:token',
      name: 'invitacion',
      component: () => import('./views/InvitacionView.vue'),
      meta: { auth: true },
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

  if (to.meta.auth && !session.user.value) {
    return { name: 'acceso', query: to.fullPath === '/' ? {} : { siguiente: to.fullPath } }
  }
  if (to.meta.admin && !session.isAdmin.value) {
    useAvisos().mostrar('La cabina de grabación es solo para administradores.', 'error')
    return { name: 'inicio' }
  }
  if (to.name === 'acceso' && session.user.value) return { name: 'inicio' }
})
