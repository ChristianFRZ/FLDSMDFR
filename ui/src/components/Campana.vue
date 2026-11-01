<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useNotificaciones } from '../composables/useNotificaciones'
import PanelAvisos from './PanelAvisos.vue'
import Icono from './icons/Icono.vue'

// Campana del encabezado: contador de no leídos y popover con los avisos.
const { items, noLeidos, panelAbierto: abierta, marcarLeidos } = useNotificaciones()
const raiz = ref<HTMLElement | null>(null)
const boton = ref<HTMLButtonElement | null>(null)

const etiqueta = computed(() =>
  noLeidos.value > 0 ? `Avisos, ${noLeidos.value} sin leer` : 'Avisos',
)

function cerrar(devolverFoco = true): void {
  abierta.value = false
  if (devolverFoco) boton.value?.focus()
}

function alternar(): void {
  abierta.value = !abierta.value
}

// Lo que queda a la vista con el panel abierto se marca como leído: al abrirlo (también desde
// la vista de invitación) y cuando llegan avisos nuevos con el panel abierto.
watch(
  [abierta, items],
  async ([abierto, lista]) => {
    if (!abierto) return
    await nextTick()
    void marcarLeidos(lista.filter((a) => !a.read).map((a) => a.id))
  },
  { immediate: true },
)

function onDocumento(evento: Event): void {
  if (!abierta.value) return
  if (evento instanceof KeyboardEvent) {
    if (evento.key === 'Escape') cerrar()
    return
  }
  if (raiz.value && !raiz.value.contains(evento.target as Node)) cerrar(false)
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
  <div ref="raiz" class="campana">
    <button
      ref="boton"
      type="button"
      class="boton-icono campana__boton"
      :aria-label="etiqueta"
      aria-haspopup="dialog"
      :aria-expanded="abierta"
      @click="alternar"
    >
      <Icono nombre="bell" :tam="20" />
      <span v-if="noLeidos > 0" class="campana__contador" data-prueba="contador" aria-hidden="true">
        {{ noLeidos > 9 ? '9+' : noLeidos }}
      </span>
    </button>
    <div v-if="abierta" class="campana__popover" role="dialog" aria-label="Avisos">
      <PanelAvisos />
    </div>
  </div>
</template>

<style scoped>
.campana {
  position: relative;
}

.campana__boton {
  position: relative;
}

.campana__contador {
  position: absolute;
  top: 0;
  right: 0;
  display: grid;
  place-items: center;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: var(--radius-pill);
  background: var(--accent);
  color: var(--on-accent);
  font-size: 10px;
  font-weight: 700;
}

.campana__popover {
  position: absolute;
  top: calc(100% + var(--space-2));
  right: 0;
  z-index: 40;
  width: min(360px, calc(100vw - 32px));
  max-height: min(520px, 70vh);
  padding: var(--space-4);
  overflow-y: auto;
  border: 1px solid var(--surface);
  border-radius: var(--radius-l);
  background: var(--bg);
  box-shadow: 0 12px 32px rgb(0 0 0 / 35%);
}
</style>
