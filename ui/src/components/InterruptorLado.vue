<script setup lang="ts">
import { computed } from 'vue'
import { useTheme } from '../composables/useTheme'

const { side, toggle } = useTheme()
const isSideB = computed(() => side.value === 'B')
const nextSide = computed(() => (isSideB.value ? 'A' : 'B'))
</script>

<template>
  <button
    type="button"
    class="interruptor-lado"
    role="switch"
    :aria-checked="isSideB"
    :title="`Cambiar a Lado ${nextSide}`"
    @click="toggle"
  >
    <svg
      class="interruptor-lado__casete"
      :class="{ 'interruptor-lado__casete--b': isSideB }"
      viewBox="0 0 24 16"
      width="24"
      height="16"
      aria-hidden="true"
    >
      <rect x="1" y="1" width="22" height="14" rx="2" fill="none" stroke="currentColor" stroke-width="2" />
      <circle cx="8" cy="8" r="2.5" fill="currentColor" />
      <circle cx="16" cy="8" r="2.5" fill="currentColor" />
    </svg>
    <span>Lado {{ side }}</span>
  </button>
</template>

<style scoped>
.interruptor-lado {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 40px;
  padding: 0 var(--space-4);
  border: 2px solid currentColor;
  border-radius: 999px;
  background: transparent;
  font-size: 13px;
  font-weight: 500;
}

@media (hover: hover) {
  .interruptor-lado:hover {
    background: color-mix(in srgb, currentColor 12%, transparent);
  }
}

.interruptor-lado__casete {
  transition: transform 200ms ease;
}

.interruptor-lado__casete--b {
  transform: rotateX(180deg);
}
</style>
