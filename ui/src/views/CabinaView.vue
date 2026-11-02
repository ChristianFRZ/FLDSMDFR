<script setup lang="ts">
import { ref } from 'vue'
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
  <section class="cabina" aria-labelledby="titulo-cabina">
    <header class="cabina__encabezado">
      <p class="antetitulo">SOLO ADMINISTRADORES</p>
      <h1 id="titulo-cabina">Cabina de grabación</h1>
    </header>

    <div class="cabina__columnas">
      <aside class="cabina__lateral" aria-label="Resumen y subida">
        <div class="tarjeta"><ResumenMetricas ref="resumen" /></div>
        <div class="tarjeta"><FormularioSubida @subida="alSubir" /></div>
      </aside>

      <div class="cabina__principal">
        <div class="tarjeta"><TablaCanciones ref="tabla" @cambio="alCambiar" /></div>
        <div class="tarjeta"><GestionUsuarios /></div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.cabina {
  display: grid;
  gap: var(--space-5);
  padding: var(--space-5);
}

.cabina__encabezado {
  display: grid;
  gap: var(--space-2);
}

.cabina__columnas {
  display: grid;
  gap: var(--space-4);
  align-items: start;
}

.cabina__lateral,
.cabina__principal {
  display: grid;
  gap: var(--space-4);
  min-width: 0;
}

.cabina .tarjeta {
  padding: var(--space-4);
}

@media (min-width: 1100px) {
  .cabina__columnas {
    grid-template-columns: minmax(300px, 380px) minmax(0, 1fr);
  }
}

@media (max-width: 700px) {
  .cabina {
    padding: var(--space-4);
  }
}
</style>
