<script setup lang="ts">
defineProps<{ etiqueta: string; girando: boolean }>()
</script>

<template>
  <div class="casete">
    <div class="casete__etiqueta">
      <h2 class="casete__nombre">{{ etiqueta }}</h2>
    </div>
    <div class="casete__ventana" role="img" aria-label="Carretes del casete">
      <svg
        v-for="lado in ['izquierdo', 'derecho']"
        :key="lado"
        class="casete__carrete"
        :class="{ girando }"
        viewBox="0 0 32 32"
        width="32"
        height="32"
        aria-hidden="true"
      >
        <circle cx="16" cy="16" r="15" fill="none" stroke="var(--paper)" stroke-width="2" />
        <circle cx="16" cy="16" r="3" fill="var(--paper)" />
        <path
          d="M16 4v9M16 19v9M4 16h9M19 16h9"
          stroke="var(--paper)"
          stroke-width="2"
          stroke-linecap="round"
        />
      </svg>
      <span class="casete__cinta" />
    </div>
  </div>
</template>

<style scoped>
.casete {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-m);
  background: var(--tape);
  box-shadow: inset 0 0 0 2px rgb(0 0 0 / 0.18);
}

.casete__etiqueta {
  padding: var(--space-2) var(--space-3);
  border-top: 6px solid var(--accent);
  border-radius: var(--radius-s);
  background: var(--paper);
  color: var(--ink);
}

.casete__nombre {
  overflow: hidden;
  font-family: var(--font-hand);
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 0;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.casete__ventana {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 78%;
  height: 46px;
  margin: 0 auto;
  padding: 0 var(--space-3);
  border-radius: 23px;
  background: rgb(0 0 0 / 0.35);
}

.casete__carrete {
  position: relative;
  z-index: 1;
  flex: none;
}

.casete__cinta {
  position: absolute;
  top: 50%;
  right: 28px;
  left: 28px;
  height: 4px;
  background: var(--accent2);
  transform: translateY(-50%);
}

.casete__carrete.girando {
  animation: girar 2s linear infinite;
}

@keyframes girar {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .casete__carrete.girando {
    animation: none;
  }
}
</style>
