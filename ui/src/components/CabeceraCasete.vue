<script setup lang="ts">
// Cabecera común de "Casete" y "Tus favoritas": portada, antetítulo, título, detalle y acciones.
defineProps<{ antetitulo: string; detalle: string }>()
</script>

<template>
  <header class="cabecera-casete">
    <div class="cabecera-casete__portada"><slot name="portada" /></div>
    <div class="cabecera-casete__texto">
      <p class="antetitulo">{{ antetitulo }}</p>
      <slot name="titulo" />
      <p class="texto-secundario">{{ detalle }}</p>
      <div class="cabecera-casete__acciones"><slot name="acciones" /></div>
    </div>
  </header>
</template>

<style scoped>
.cabecera-casete {
  display: flex;
  align-items: flex-end;
  gap: var(--space-5);
}

.cabecera-casete__portada {
  position: relative;
  flex-shrink: 0;
}

.cabecera-casete__texto {
  display: grid;
  gap: var(--space-2);
  min-width: 0;
}

.cabecera-casete__acciones {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-2);
}

@media (max-width: 700px) {
  .cabecera-casete {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
