<script setup lang="ts">
import { RouterLink } from 'vue-router'
import Icono from './icons/Icono.vue'
import type { NombreIcono } from './icons/iconos'

const DESTINOS: ReadonlyArray<{ to: string; texto: string; icono: NombreIcono }> = [
  { to: '/', texto: 'Inicio', icono: 'house' },
  { to: '/catalogo', texto: 'Catálogo', icono: 'compass' },
  { to: '/biblioteca', texto: 'Biblioteca', icono: 'library' },
  { to: '/streaming', texto: 'Streaming', icono: 'radio' },
]
</script>

<template>
  <nav class="movil" aria-label="Principal">
    <RouterLink
      v-for="d in DESTINOS"
      :key="d.to"
      :to="d.to"
      class="movil__destino"
      :exact-active-class="d.to === '/' ? 'movil__destino--activo' : ''"
      :active-class="d.to === '/' ? '' : 'movil__destino--activo'"
    >
      <Icono :nombre="d.icono" :tam="20" />
      <span>{{ d.texto }}</span>
    </RouterLink>
  </nav>
</template>

<style scoped>
.movil {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  border-top: 1px solid var(--rule);
}

.movil__destino {
  display: grid;
  justify-items: center;
  gap: 2px;
  min-height: 52px;
  padding: var(--space-2) 0;
  color: var(--ink-muted);
  font-size: 11px;
  text-decoration: none;
}

.movil__destino--activo {
  color: var(--ink);
  font-weight: 600;
}
</style>
