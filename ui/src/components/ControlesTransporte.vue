<script setup lang="ts">
import { computed } from 'vue'
import { usePlayer } from '../composables/usePlayer'
import Icono from './icons/Icono.vue'

// Aleatorio, anterior, play/pausa, siguiente y repetir: compartidos por la barra y "Sonando ahora".
withDefaults(defineProps<{ grande?: boolean }>(), { grande: false })

const player = usePlayer()
const { current, isPlaying, shuffle, repeat, upcoming } = player

const ETIQUETA_REPETIR = { off: 'Repetir: apagado', all: 'Repetir: todo', one: 'Repetir: esta canción' }
const etiquetaRepetir = computed(() => ETIQUETA_REPETIR[repeat.value])
const haySiguiente = computed(() => upcoming.value.length > 0 || repeat.value === 'all')
</script>

<template>
  <div class="transporte" :class="{ 'transporte--grande': grande }">
    <button
      type="button"
      class="boton-icono"
      :class="{ 'transporte--activo': shuffle }"
      aria-label="Aleatorio"
      :aria-pressed="shuffle"
      @click="player.toggleShuffle()"
    >
      <Icono nombre="shuffle" :tam="grande ? 22 : 16" />
    </button>
    <button type="button" class="boton-icono" aria-label="Anterior" :disabled="!current" @click="player.prev()">
      <Icono nombre="skip-back" :tam="grande ? 24 : 18" />
    </button>
    <button
      type="button"
      class="transporte__play"
      :aria-label="isPlaying ? 'Pausar' : 'Reproducir'"
      :disabled="!current"
      @click="player.toggle()"
    >
      <Icono :nombre="isPlaying ? 'pause' : 'play'" :tam="grande ? 26 : 16" />
    </button>
    <button
      type="button"
      class="boton-icono"
      aria-label="Siguiente"
      :disabled="!current || !haySiguiente"
      @click="player.next()"
    >
      <Icono nombre="skip-forward" :tam="grande ? 24 : 18" />
    </button>
    <button
      type="button"
      class="boton-icono"
      :class="{ 'transporte--activo': repeat !== 'off' }"
      data-prueba="repetir"
      :aria-label="etiquetaRepetir"
      :aria-pressed="repeat !== 'off'"
      @click="player.cycleRepeat()"
    >
      <Icono :nombre="repeat === 'one' ? 'repeat-1' : 'repeat'" :tam="grande ? 22 : 16" />
    </button>
  </div>
</template>

<style scoped>
.transporte {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
}

.transporte--grande {
  gap: var(--space-5);
}

.transporte .boton-icono {
  color: var(--ink-muted);
}

.transporte .transporte--activo {
  color: var(--ink);
}

/* Punto bajo aleatorio/repetir activos: el estado no depende solo del color. */
.transporte--activo {
  position: relative;
}

.transporte--activo::after {
  content: '';
  position: absolute;
  bottom: 1px;
  left: 50%;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: currentColor;
  transform: translateX(-50%);
}

.transporte__play {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 50%;
  background: var(--surface-active);
  color: var(--ink-on-active);
}

.transporte--grande .transporte__play {
  width: 64px;
  height: 64px;
  background: var(--accent);
  color: var(--on-accent);
}

@media (hover: hover) {
  .transporte__play:not(:disabled):hover {
    background: var(--accent);
    color: var(--on-accent);
  }
}
</style>
