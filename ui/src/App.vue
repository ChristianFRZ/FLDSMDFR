<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import Aviso from './components/Aviso.vue'
import InterruptorLado from './components/InterruptorLado.vue'
import { usePlayer } from './composables/usePlayer'

// Las vistas con encabezado propio (la casetera) colocan ahí su InterruptorLado.
const route = useRoute()

// El único <audio> vive aquí para que la música siga al pasar de la casetera a la cabina.
const audio = ref<HTMLAudioElement | null>(null)
onMounted(() => {
  if (audio.value) usePlayer().attach(audio.value)
})
</script>

<template>
  <div class="app">
    <header v-if="!route.meta.encabezadoPropio" class="app__barra">
      <InterruptorLado />
    </header>
    <main class="app__contenido">
      <RouterView />
    </main>
    <Aviso />
    <audio ref="audio" preload="metadata" />
  </div>
</template>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  min-height: 100dvh;
}

.app__barra {
  display: flex;
  justify-content: flex-end;
  padding: var(--space-3) var(--space-4);
}

.app__contenido {
  flex: 1;
  min-width: 0;
}
</style>
