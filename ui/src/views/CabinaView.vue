<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import FormularioSubida from '../components/FormularioSubida.vue'
import GestionUsuarios from '../components/GestionUsuarios.vue'
import ResumenMetricas from '../components/ResumenMetricas.vue'
import TablaCanciones from '../components/TablaCanciones.vue'
import type { SongOut } from '../api/types'

// Referencias a los componentes hijos: la subida y los retiros actualizan tabla y resumen sin recargar.
const tabla = ref<InstanceType<typeof TablaCanciones> | null>(null)
const resumen = ref<InstanceType<typeof ResumenMetricas> | null>(null)

function alSubir(cancion: SongOut): void {
  tabla.value?.agregar(cancion)
  void resumen.value?.recargar()
}

function alCambiar(): void {
  void resumen.value?.recargar()
}
</script>

<template>
  <div class="cabina">

    <aside class="cabina__deck" aria-label="Resumen y subida">
      <header class="cabina__encabezado">
        <h1>Cabina de grabación</h1>
        <RouterLink to="/" class="cabina__volver">Volver a la casetera</RouterLink>
      </header>
      <ResumenMetricas ref="resumen" />
      <FormularioSubida @subida="alSubir" />
    </aside>

    <div class="cabina__tienda">
      <TablaCanciones ref="tabla" @cambio="alCambiar" />
      <GestionUsuarios />
    </div>
  </div>
</template>

<style scoped>
.cabina {
  display: grid;
  gap: var(--space-5);
}

.cabina__barra {
  display: flex;
  justify-content: flex-end;
  padding: var(--space-3) var(--space-4);
}

.cabina__deck {
  display: grid;
  gap: var(--space-5);
  align-content: start;
  padding: var(--space-5) var(--space-4);
  background: var(--deck);
  color: var(--deck-ink);
}

.cabina__encabezado {
  display: grid;
  gap: var(--space-2);
}

.cabina__volver {
  display: inline-flex;
  align-items: center;
  justify-self: start;
  min-height: 40px;
  color: inherit;
  font-weight: 500;
  text-underline-offset: 3px;
}

.cabina__tienda {
  display: grid;
  gap: var(--space-5);
  align-content: start;
  min-width: 0;
  padding: 0 var(--space-4) var(--space-5);
}

@media (min-width: 900px) {
  .cabina {
    grid-template-columns: minmax(320px, 400px) minmax(0, 1fr);
    grid-template-rows: auto 1fr;
    gap: 0;
    min-height: 100dvh;
  }

  .cabina__barra {
    grid-column: 2;
    grid-row: 1;
  }

  .cabina__deck {
    grid-column: 1;
    grid-row: 1 / span 2;
  }

  .cabina__tienda {
    grid-column: 2;
    grid-row: 2;
    padding: 0 var(--space-5) var(--space-5);
  }
}
</style>
