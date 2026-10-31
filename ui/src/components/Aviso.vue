<script setup lang="ts">
import { useAvisos } from '../composables/useAvisos'

const { avisos } = useAvisos()
</script>

<template>
  <!-- La región existe siempre para que los lectores de pantalla anuncien los avisos al aparecer. -->
  <div class="avisos" role="status" aria-live="polite">
    <p
      v-for="aviso in avisos"
      :key="aviso.id"
      class="aviso"
      :class="`aviso--${aviso.tipo}`"
    >
      <svg class="aviso__icono" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
        <path
          v-if="aviso.tipo === 'error'"
          d="M4 4l8 8M12 4l-8 8"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
        />
        <g v-else fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <circle cx="8" cy="8" r="6.5" />
          <path d="M8 7.5V11M8 5v.01" />
        </g>
      </svg>
      <span>{{ aviso.texto }}</span>
    </p>
  </div>
</template>

<style scoped>
.avisos {
  position: fixed;
  right: var(--space-4);
  bottom: var(--space-4);
  left: var(--space-4);
  z-index: 10;
  display: grid;
  gap: var(--space-2);
  justify-items: end;
  pointer-events: none;
}

.aviso {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  max-width: 420px;
  margin: 0;
  padding: var(--space-3) var(--space-4);
  border-left: 4px solid var(--ink);
  border-radius: var(--radius-m);
  background: var(--paper);
  color: var(--ink);
  pointer-events: auto;
}

.aviso--error {
  border-left-color: var(--danger);
}

.aviso__icono {
  flex: none;
  margin-top: var(--space-1);
}

.aviso--error .aviso__icono {
  color: var(--danger);
}
</style>
