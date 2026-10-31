<script setup lang="ts">
// Aviso en el lugar del contenido (DESIGN.md §6.0 y §6.9): error con "Reintentar" o degradado.
withDefaults(defineProps<{ tipo?: 'error' | 'aviso'; reintentar?: boolean }>(), {
  tipo: 'error',
  reintentar: false,
})
defineEmits<{ reintentar: [] }>()
</script>

<template>
  <div class="aviso-linea" :class="`aviso-linea--${tipo}`" role="alert">
    <svg class="aviso-linea__icono" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
      <path
        v-if="tipo === 'error'"
        d="M4 4l8 8M12 4l-8 8"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
      />
      <g v-else fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" stroke-linecap="round">
        <path d="M8 1.5l6.5 12h-13z" />
        <path d="M8 6.5v3M8 11.5v.01" />
      </g>
    </svg>
    <p class="aviso-linea__texto"><slot /></p>
    <button v-if="reintentar" type="button" class="aviso-linea__accion" @click="$emit('reintentar')">
      Reintentar
    </button>
  </div>
</template>

<style scoped>
.aviso-linea {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2) var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-left: 4px solid var(--danger);
  border-radius: var(--radius-m);
  background: var(--paper);
  color: var(--ink);
}

.aviso-linea--aviso {
  border-left-color: var(--accent2);
}

.aviso-linea__icono {
  flex: none;
}

.aviso-linea--error .aviso-linea__icono {
  color: var(--danger);
}

.aviso-linea__texto {
  flex: 1 1 12rem;
  min-width: 0;
  margin: 0;
}

.aviso-linea__accion {
  min-height: 40px;
  padding: 0 var(--space-4);
  border: 2px solid currentColor;
  border-radius: 999px;
  background: transparent;
  font-weight: 500;
}

@media (hover: hover) {
  .aviso-linea__accion:hover {
    background: color-mix(in srgb, currentColor 12%, transparent);
  }
}
</style>
