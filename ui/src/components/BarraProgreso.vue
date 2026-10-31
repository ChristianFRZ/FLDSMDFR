<script setup lang="ts">
import { computed } from 'vue'
import { formatTime } from '../composables/formatTime'

const props = defineProps<{
  currentTime: number
  duration: number
  buffered: Array<[number, number]>
}>()
const emit = defineEmits<{ seek: [seconds: number] }>()

const PASO = 5
const PASO_GRANDE = 30

const habilitada = computed(() => props.duration > 0)
const porcentaje = (segundos: number) =>
  habilitada.value ? Math.min(Math.max((segundos / props.duration) * 100, 0), 100) : 0
const reproducido = computed(() => porcentaje(props.currentTime))
const segmentos = computed(() =>
  props.buffered.map(([inicio, fin]) => ({
    left: porcentaje(inicio),
    width: Math.max(porcentaje(fin) - porcentaje(inicio), 0),
  })),
)
const valuetext = computed(
  () => `${formatTime(props.currentTime)} de ${formatTime(props.duration)}`,
)

function pedirSeek(segundos: number): void {
  if (!habilitada.value) return
  emit('seek', Math.min(Math.max(segundos, 0), props.duration))
}

function onKeydown(event: KeyboardEvent): void {
  const destinos: Record<string, number> = {
    ArrowRight: props.currentTime + PASO,
    ArrowUp: props.currentTime + PASO,
    ArrowLeft: props.currentTime - PASO,
    ArrowDown: props.currentTime - PASO,
    PageUp: props.currentTime + PASO_GRANDE,
    PageDown: props.currentTime - PASO_GRANDE,
    Home: 0,
    End: props.duration,
  }
  const destino = destinos[event.key]
  if (destino === undefined) return
  event.preventDefault()
  pedirSeek(destino)
}

function seekDesdePuntero(event: MouseEvent | PointerEvent): void {
  const caja = (event.currentTarget as HTMLElement).getBoundingClientRect()
  if (caja.width <= 0) return
  const fraccion = Math.min(Math.max((event.clientX - caja.left) / caja.width, 0), 1)
  pedirSeek(fraccion * props.duration)
}

// Arrastre: pointerdown fija el puntero al elemento y los movimientos siguientes hacen seek.
// El `click` que sigue a un pointerdown ya está atendido; solo se usa sin pointerdown previo.
let arrastrando = false
let atendidoPorPuntero = false

function onPointerdown(event: PointerEvent): void {
  if (!habilitada.value) return
  arrastrando = true
  atendidoPorPuntero = true
  ;(event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId)
  seekDesdePuntero(event)
}
function onPointermove(event: PointerEvent): void {
  if (arrastrando) seekDesdePuntero(event)
}
function onPointerup(): void {
  arrastrando = false
}
function onClick(event: MouseEvent): void {
  if (atendidoPorPuntero) {
    atendidoPorPuntero = false
    return
  }
  seekDesdePuntero(event)
}
</script>

<template>
  <div
    class="barra"
    :class="{ 'barra--inactiva': !habilitada }"
    role="slider"
    tabindex="0"
    aria-label="Progreso de la canción"
    aria-valuemin="0"
    :aria-valuemax="duration"
    :aria-valuenow="currentTime"
    :aria-valuetext="valuetext"
    :aria-disabled="!habilitada"
    @keydown="onKeydown"
    @pointerdown="onPointerdown"
    @pointermove="onPointermove"
    @pointerup="onPointerup"
    @pointercancel="onPointerup"
    @click="onClick"
  >
    <div class="barra__pista">
      <span
        v-for="(segmento, i) in segmentos"
        :key="i"
        class="segmento-descargado"
        :style="{ left: `${segmento.left}%`, width: `${segmento.width}%` }"
      />
      <span class="barra__reproducido" :style="{ width: `${reproducido}%` }" />
    </div>
    <span v-if="habilitada" class="barra__tirador" :style="{ left: `${reproducido}%` }" />
  </div>
</template>

<style scoped>
.barra {
  position: relative;
  display: flex;
  align-items: center;
  height: 40px;
  cursor: pointer;
  touch-action: none;
}

.barra--inactiva {
  cursor: default;
}

.barra__pista {
  position: relative;
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: rgb(255 255 255 / 0.2);
  overflow: hidden;
}

.segmento-descargado {
  position: absolute;
  top: 0;
  bottom: 0;
  background: var(--deck-ink);
  opacity: 0.35;
}

/* --accent2 y no --accent: 3.85:1 sobre --deck en el Lado A (DESIGN.md §3.2, restricción 4). */
.barra__reproducido {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  background: var(--accent2);
}

.barra__tirador {
  position: absolute;
  top: 50%;
  width: 16px;
  height: 16px;
  border: 2px solid var(--deck);
  border-radius: 50%;
  background: var(--accent2);
  transform: translate(-50%, -50%);
  pointer-events: none;
}
</style>
