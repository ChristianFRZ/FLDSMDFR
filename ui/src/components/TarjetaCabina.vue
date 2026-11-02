<script setup lang="ts">
import { RouterLink } from 'vue-router'
import Icono from './icons/Icono.vue'
</script>

<template>
  <aside class="cabina" aria-labelledby="titulo-tarjeta-cabina">
    <Icono nombre="disc-3" :tam="23" />
    <h2 id="titulo-tarjeta-cabina" class="cabina__titulo">Cabina de grabación · Administrador</h2>
    <p class="cabina__texto">Sube canciones, retira temas y cambia roles desde la Cabina.</p>
    <RouterLink to="/cabina" class="cabina__enlace">
      Abrir Cabina
      <Icono nombre="arrow-up-right" :tam="14" />
    </RouterLink>
  </aside>
</template>

<style scoped>
.cabina {
  display: grid;
  gap: 10px;
  padding: var(--space-4);
  border-radius: var(--radius-l);
  background: var(--surface-active);
  color: var(--ink-on-active);
}

.cabina__titulo {
  font-size: 20px;
  line-height: 1.2;
  color: var(--ink-on-active);
}

.cabina__texto {
  font-size: 11px;
  line-height: 1.5;
}

.cabina__enlace {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  width: fit-content;
  font-size: 11px;
  font-weight: 600;
  text-decoration: none;
}
</style>
