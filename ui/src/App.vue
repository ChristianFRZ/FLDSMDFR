<script setup lang="ts">
import { RouterView, useRoute } from 'vue-router'
import Aviso from './components/Aviso.vue'
import InterruptorLado from './components/InterruptorLado.vue'

// Las vistas con encabezado propio (la casetera) colocan ahí su InterruptorLado.
const route = useRoute()
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
