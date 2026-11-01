<script setup lang="ts">
import BarraLateral from '../components/BarraLateral.vue'
import EncabezadoSuperior from '../components/EncabezadoSuperior.vue'
import NavegacionMovil from '../components/NavegacionMovil.vue'
</script>

<template>
  <div class="layout">
    <BarraLateral class="layout__lateral">
      <template #biblioteca><slot name="biblioteca" /></template>
    </BarraLateral>
    <div class="layout__columna">
      <EncabezadoSuperior>
        <template #campana><slot name="campana" /></template>
      </EncabezadoSuperior>
      <main id="contenido" class="layout__contenido" tabindex="-1">
        <slot />
      </main>
    </div>
    <NavegacionMovil class="layout__movil" />
    <div class="layout__reproductor">
      <slot name="reproductor" />
    </div>
  </div>
</template>

<style scoped>
.layout {
  display: grid;
  grid-template-columns: var(--sidebar-width) minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr) auto;
  grid-template-areas:
    'lateral columna'
    'reproductor reproductor';
  height: 100vh;
  height: 100dvh;
}

.layout__lateral {
  grid-area: lateral;
  min-height: 0;
}

.layout__columna {
  grid-area: columna;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.layout__contenido {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 20px var(--space-6) var(--space-5);
}

.layout__contenido:focus {
  outline: none;
}

.layout__movil {
  display: none;
  grid-area: movil;
}

.layout__reproductor {
  grid-area: reproductor;
}

@media (max-width: 899px) {
  .layout {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: minmax(0, 1fr) auto auto;
    grid-template-areas:
      'columna'
      'reproductor'
      'movil';
  }

  .layout__lateral {
    display: none;
  }

  .layout__movil {
    display: grid;
  }

  .layout__contenido {
    padding: var(--space-4);
  }
}
</style>
