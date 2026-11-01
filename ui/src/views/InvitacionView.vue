<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiError } from '../api/http'
import * as invites from '../api/invites'
import { useAvisos } from '../composables/useAvisos'
import { useNotificaciones } from '../composables/useNotificaciones'

// Reclama un enlace de invitación y lleva a Avisos para aceptarla (o al casete si ya eres parte).
const route = useRoute()
const router = useRouter()
const { mostrar } = useAvisos()
const notificaciones = useNotificaciones()

onMounted(async () => {
  const token = String(route.params.token ?? '')
  try {
    const reclamo = await invites.claim(token)
    if (reclamo.status === 'member' || reclamo.status === 'accepted') {
      mostrar('Ya formas parte de este casete.', 'info')
      await router.replace(`/casete/${reclamo.playlist_id}`)
      return
    }
    await router.replace('/')
    await notificaciones.refrescar()
    notificaciones.abrirPanel()
  } catch (e) {
    const invalido = e instanceof ApiError && (e.status === 404 || e.status === 410)
    mostrar(invalido ? 'Este enlace ya no es válido.' : 'No pudimos abrir la invitación. Vuelve a intentarlo.', 'error')
    await router.replace('/')
  }
})
</script>

<template>
  <section class="invitacion" aria-live="polite">
    <p class="texto-secundario">Abriendo la invitación…</p>
  </section>
</template>

<style scoped>
.invitacion {
  padding: var(--space-5);
}
</style>
