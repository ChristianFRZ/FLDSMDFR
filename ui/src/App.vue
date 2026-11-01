<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import Aviso from './components/Aviso.vue'
import Biblioteca from './components/Biblioteca.vue'
import Campana from './components/Campana.vue'
import Reproductor from './components/Reproductor.vue'
import LayoutPrincipal from './layouts/LayoutPrincipal.vue'
import { useCasetes } from './composables/useCasetes'
import { useFavoritos } from './composables/useFavoritos'
import { useNotificaciones } from './composables/useNotificaciones'
import { usePlayer } from './composables/usePlayer'
import { useSeguidos } from './composables/useSeguidos'
import { useSession } from './composables/useSession'

const route = useRoute()

// El único <audio> vive aquí para que la música siga al cambiar de vista.
const audio = ref<HTMLAudioElement | null>(null)
onMounted(() => {
  if (audio.value) usePlayer().attach(audio.value)
})

// Corazones, casetes, seguidos y avisos dependen de la cuenta: se cargan al entrar y se vacían al salir.
const session = useSession()
const favoritos = useFavoritos()
const notificaciones = useNotificaciones()
const casetes = useCasetes()
const seguidos = useSeguidos()
watch(
  () => session.user.value?.id,
  (id) => {
    notificaciones.reiniciar()
    if (id) {
      void favoritos.cargar()
      void casetes.cargar()
      void seguidos.cargar()
      notificaciones.iniciar()
    } else {
      favoritos.reiniciar()
      seguidos.reiniciar()
    }
  },
  { immediate: true },
)
</script>

<template>
  <!-- Hasta resolver la primera ruta no se sabe si lleva layout: no se pinta nada. -->
  <template v-if="route.matched.length === 0" />
  <RouterView v-else-if="route.meta.sinLayout" />
  <LayoutPrincipal v-else>
    <RouterView />
    <template #biblioteca><Biblioteca /></template>
    <template #campana><Campana /></template>
    <template #reproductor><Reproductor /></template>
  </LayoutPrincipal>
  <Aviso />
  <audio ref="audio" preload="metadata" />
</template>
