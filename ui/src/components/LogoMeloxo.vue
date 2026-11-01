<script setup lang="ts">
import { computed } from 'vue'
import simbolo from '../assets/logo-meloxo.svg?raw'
import simboloPequeno from '../assets/logo-meloxo-pequeno.svg?raw'

// Sol-carrete: bajo 24 px se usa el corte pequeño (sin dientes en el carrete). DESIGN.md §5.
const props = withDefaults(defineProps<{ size?: number; conTexto?: boolean }>(), {
  size: 29,
  conTexto: true,
})
const svg = computed(() => (props.size < 24 ? simboloPequeno : simbolo))
</script>

<template>
  <span class="logo" :class="{ 'logo--con-texto': conTexto }">
    <span
      class="logo__simbolo"
      :style="{ width: `${size}px`, height: `${size}px` }"
      :role="conTexto ? undefined : 'img'"
      :aria-label="conTexto ? undefined : 'MELOXO'"
      :aria-hidden="conTexto ? 'true' : undefined"
      v-html="svg"
    />
    <template v-if="conTexto">
      <span class="logo__texto">MELOXO</span>
      <span class="logo__punto" aria-hidden="true" />
    </template>
  </span>
</template>

<style scoped>
.logo {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  color: var(--accent);
}

.logo__simbolo {
  display: inline-flex;
  flex-shrink: 0;
}

.logo__simbolo :deep(svg) {
  width: 100%;
  height: 100%;
}

.logo__texto {
  font-family: var(--font-display);
  font-size: 24px;
  letter-spacing: -1.5px;
  line-height: 1;
}

.logo__punto {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
</style>
