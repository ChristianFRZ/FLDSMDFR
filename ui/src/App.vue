<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import Aviso from './components/Aviso.vue'
import ControlesReproductor from './components/ControlesReproductor.vue'
import LayoutPrincipal from './layouts/LayoutPrincipal.vue'
import { usePlayer } from './composables/usePlayer'

const route = useRoute()

// El único <audio> vive aquí para que la música siga al cambiar de vista.
const audio = ref<HTMLAudioElement | null>(null)
onMounted(() => {
  if (audio.value) usePlayer().attach(audio.value)
})
</script>

<template>
  <!-- Hasta resolver la primera ruta no se sabe si lleva layout: no se pinta nada. -->
  <template v-if="route.matched.length === 0" />
  <RouterView v-else-if="route.meta.sinLayout" />
  <LayoutPrincipal v-else>
    <RouterView />
    <template #reproductor><ControlesReproductor /></template>
  </LayoutPrincipal>
  <Aviso />
  <audio ref="audio" preload="metadata" />
</template>
