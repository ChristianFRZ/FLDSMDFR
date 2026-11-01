<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

// Ventanita de casete con dos carretes que giran mientras suena (DESIGN.md §7.7).
const props = defineProps<{ girando: boolean }>()

const consulta = typeof matchMedia === 'function' ? matchMedia('(prefers-reduced-motion: reduce)') : null
const reducido = ref(consulta?.matches ?? false)
const alCambiar = (e: MediaQueryListEvent) => (reducido.value = e.matches)
onMounted(() => consulta?.addEventListener?.('change', alCambiar))
onBeforeUnmount(() => consulta?.removeEventListener?.('change', alCambiar))

const gira = computed(() => props.girando && !reducido.value)
</script>

<template>
  <div class="carretes" :class="{ 'carretes--girando': gira }" aria-hidden="true">
    <svg viewBox="0 0 240 110" class="carretes__dibujo">
      <rect x="4" y="4" width="232" height="102" rx="12" class="carretes__cuerpo" />
      <rect x="44" y="30" width="152" height="50" rx="25" class="carretes__ventana" />
      <g class="carretes__carrete" style="transform-origin: 80px 55px">
        <circle cx="80" cy="55" r="18" class="carretes__cinta" />
        <path d="M80 41v28M66 55h28M70 45l20 20M90 45l-20 20" class="carretes__radios" />
        <circle cx="80" cy="55" r="5" class="carretes__eje" />
      </g>
      <g class="carretes__carrete" style="transform-origin: 160px 55px">
        <circle cx="160" cy="55" r="18" class="carretes__cinta" />
        <path d="M160 41v28M146 55h28M150 45l20 20M170 45l-20 20" class="carretes__radios" />
        <circle cx="160" cy="55" r="5" class="carretes__eje" />
      </g>
    </svg>
  </div>
</template>

<style scoped>
.carretes__dibujo {
  display: block;
  width: 100%;
  max-width: 320px;
}

.carretes__cuerpo {
  fill: var(--surface);
}

.carretes__ventana {
  fill: var(--bg);
}

.carretes__cinta {
  fill: var(--surface-active);
  stroke: var(--accent);
  stroke-width: 2;
}

.carretes__radios {
  stroke: var(--accent);
  stroke-width: 2;
  stroke-linecap: round;
}

.carretes__eje {
  fill: var(--accent);
}

.carretes--girando .carretes__carrete {
  animation: girar 2.4s linear infinite;
}

@keyframes girar {
  to {
    transform: rotate(360deg);
  }
}
</style>
