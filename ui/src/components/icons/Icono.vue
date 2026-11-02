<script setup lang="ts">
import { computed } from 'vue'
import { ICONOS, type NombreIcono } from './iconos'

// Icono decorativo: el texto accesible lo pone el botón o enlace que lo contiene.
const props = withDefaults(defineProps<{ nombre: NombreIcono; tam?: number }>(), { tam: 20 })
const cuerpo = computed(() => ICONOS[props.nombre])
</script>

<template>
  <svg
    class="icono"
    xmlns="http://www.w3.org/2000/svg"
    :width="tam"
    :height="tam"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    focusable="false"
    v-html="cuerpo"
  />
</template>

<style scoped>
.icono {
  flex-shrink: 0;
}
</style>
