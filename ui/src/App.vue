<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import Aviso from './components/Aviso.vue'
import Reproductor from './components/Reproductor.vue'
import LayoutPrincipal from './layouts/LayoutPrincipal.vue'
import { useFavoritos } from './composables/useFavoritos'
import { usePlayer } from './composables/usePlayer'
import { useSession } from './composables/useSession'

const route = useRoute()

// El único <audio> vive aquí para que la música siga al cambiar de vista.
const audio = ref<HTMLAudioElement | null>(null)
onMounted(() => {
  if (audio.value) usePlayer().attach(audio.value)
})

// Los corazones dependen de la cuenta: se cargan al entrar y se vacían al salir.
const session = useSession()
const favoritos = useFavoritos()
watch(
  () => session.user.value?.id,
  (id) => (id ? void favoritos.cargar() : favoritos.reiniciar()),
  { immediate: true },
)
</script>

<template>
  <!-- Hasta resolver la primera ruta no se sabe si lleva layout: no se pinta nada. -->
  <template v-if="route.matched.length === 0" />
  <RouterView v-else-if="route.meta.sinLayout" />
  <LayoutPrincipal v-else>
    <RouterView />
    <template #reproductor><Reproductor /></template>
  </LayoutPrincipal>
  <Aviso />
  <audio ref="audio" preload="metadata" />
</template>
