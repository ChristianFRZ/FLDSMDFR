import { createRouter, createWebHistory } from 'vue-router'

// Las vistas se cargan bajo demanda. El guard de sesión/rol se completa en la Task 9.
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
