<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useCasetes } from '../composables/useCasetes'
import DestinosGrabar from './DestinosGrabar.vue'
import Icono from './icons/Icono.vue'

// Botón + con popover "Grabar en casete" (DESIGN.md §7.7).
defineProps<{ songId: string; titulo: string }>()
const emit = defineEmits<{ grabado: [caseteId: string] }>()
const { casetes, cargar } = useCasetes()

const abierto = ref(false)
const raiz = ref<HTMLElement | null>(null)
const disparador = ref<HTMLButtonElement | null>(null)

async function abrir(): Promise<void> {
  abierto.value = !abierto.value
  if (!abierto.value) return
  if (casetes.value.length === 0) await cargar()
  await nextTick()
  raiz.value?.querySelector<HTMLElement>('[data-prueba="destino"], [data-prueba="nuevo-casete"]')?.focus()
}

function cerrar(devolverFoco = true): void {
  abierto.value = false
  if (devolverFoco) disparador.value?.focus()
}

function onTerminado(id: string | null): void {
  cerrar()
  if (id) emit('grabado', id)
}

function onDocumento(evento: Event): void {
  if (!abierto.value) return
  if (evento instanceof KeyboardEvent) {
    if (evento.key === 'Escape') cerrar()
  } else if (raiz.value && !raiz.value.contains(evento.target as Node)) {
    cerrar(false)
  }
}
onMounted(() => {
  document.addEventListener('keydown', onDocumento)
  document.addEventListener('pointerdown', onDocumento)
})
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onDocumento)
  document.removeEventListener('pointerdown', onDocumento)
})
</script>

<template>
  <div ref="raiz" class="selector">
    <button
      ref="disparador"
      type="button"
      class="boton-icono"
      :aria-label="`Grabar «${titulo}» en un casete`"
      aria-haspopup="dialog"
      :aria-expanded="abierto"
      @click="abrir"
    >
      <Icono nombre="plus" :tam="18" />
    </button>

    <div v-if="abierto" class="selector__popover popover" role="dialog" :aria-label="`Grabar «${titulo}»`">
      <DestinosGrabar :song-id="songId" @terminado="onTerminado" />
    </div>
  </div>
</template>

<style scoped>
.selector {
  position: relative;
  display: inline-flex;
}

.selector__popover {
  top: calc(100% + var(--space-1));
  right: 0;
}
</style>
