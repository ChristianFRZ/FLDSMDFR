<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { iniciales } from '../composables/texto'

// Portada subida (canción o casete). Sin imagen, o si falla al cargar, marcador con iniciales.
const props = withDefaults(
  defineProps<{ src: string | null; titulo: string; tam?: number; radio?: 's' | 'm' }>(),
  { tam: 44, radio: 's' },
)
const fallo = ref(false)
watch(
  () => props.src,
  () => (fallo.value = false),
)
const mostrarImagen = computed(() => !!props.src && !fallo.value)
</script>

<template>
  <span
    class="portada"
    :class="`portada--${radio}`"
    :style="{ width: `${tam}px`, height: `${tam}px`, fontSize: `${Math.max(tam / 3.2, 9)}px` }"
    aria-hidden="true"
  >
    <img v-if="mostrarImagen" :src="src!" alt="" loading="lazy" @error="fallo = true" />
    <span v-else>{{ iniciales(titulo) }}</span>
  </span>
</template>

<style scoped>
.portada {
  display: inline-grid;
  flex-shrink: 0;
  place-items: center;
  overflow: hidden;
  background: var(--surface-active);
  color: var(--ink-on-active);
  font-weight: 600;
}

.portada--s {
  border-radius: var(--radius-s);
}

.portada--m {
  border-radius: var(--radius-m);
}

.portada img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>
