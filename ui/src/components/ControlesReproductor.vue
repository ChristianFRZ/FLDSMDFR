<script setup lang="ts">
import { computed } from 'vue'
import { usePlayer } from '../composables/usePlayer'
import { formatTime } from '../composables/formatTime'
import BarraProgreso from './BarraProgreso.vue'

const player = usePlayer()
const { current, queue, isPlaying, currentTime, duration, buffered, volume } = player

const indice = computed(() => queue.value.findIndex((s) => s.id === current.value?.id))
const hayAnterior = computed(() => indice.value > 0 || currentTime.value > 3)
const haySiguiente = computed(() => indice.value >= 0 && indice.value < queue.value.length - 1)
const volumenPorcentaje = computed(() => Math.round(volume.value * 100))

function onVolumen(event: Event): void {
  player.setVolume(Number((event.target as HTMLInputElement).value) / 100)
}
</script>

<template>
  <section class="controles" aria-label="Reproductor">
    <div class="controles__fila">
      <button
        type="button"
        class="boton-icono"
        aria-label="Anterior"
        :disabled="!current || !hayAnterior"
        @click="player.prev()"
      >
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
          <path d="M6 5v14M19 5L9 12l10 7z" fill="currentColor" stroke="currentColor" stroke-width="2" stroke-linejoin="round" />
        </svg>
      </button>
      <button
        type="button"
        class="boton-play"
        :aria-label="isPlaying ? 'Pausar' : 'Reproducir'"
        :disabled="!current"
        @click="player.toggle()"
      >
        <svg v-if="isPlaying" viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
          <path d="M7 5v14M17 5v14" stroke="currentColor" stroke-width="4" stroke-linecap="round" />
        </svg>
        <svg v-else viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
          <path d="M7 4l13 8-13 8z" fill="currentColor" stroke="currentColor" stroke-width="2" stroke-linejoin="round" />
        </svg>
      </button>
      <button
        type="button"
        class="boton-icono"
        aria-label="Siguiente"
        :disabled="!haySiguiente"
        @click="player.next()"
      >
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
          <path d="M18 5v14M5 5l10 7-10 7z" fill="currentColor" stroke="currentColor" stroke-width="2" stroke-linejoin="round" />
        </svg>
      </button>

      <div class="controles__meta">
        <p class="controles__titulo">{{ current ? current.title : 'Nada suena todavía' }}</p>
        <p v-if="current" class="controles__detalle">
          {{ current.artist }} · {{ formatTime(currentTime) }} / {{ formatTime(duration) }}
        </p>
      </div>

      <label class="controles__volumen">
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
          <path d="M4 9h4l5-4v14l-5-4H4z" fill="currentColor" />
          <path d="M16 9c1.5 1.5 1.5 4.5 0 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
        </svg>
        <input
          type="range"
          min="0"
          max="100"
          step="5"
          aria-label="Volumen"
          :value="volumenPorcentaje"
          @input="onVolumen"
        />
      </label>
    </div>

    <BarraProgreso
      :current-time="currentTime"
      :duration="duration"
      :buffered="buffered"
      @seek="player.seek"
    />
  </section>
</template>

<style scoped>
.controles {
  display: grid;
  gap: var(--space-2);
  color: var(--deck-ink);
}

.controles__fila {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.boton-icono,
.boton-play {
  display: inline-flex;
  flex: none;
  align-items: center;
  justify-content: center;
  padding: 0;
  border-radius: 50%;
}

.boton-icono {
  width: 40px;
  height: 40px;
  border: 2px solid currentColor;
  background: transparent;
  color: var(--deck-ink);
}

.boton-play {
  width: 52px;
  height: 52px;
  border: 0;
  background: var(--accent);
  color: var(--on-accent);
}

.boton-icono:active:not(:disabled),
.boton-play:active:not(:disabled) {
  transform: scale(0.96);
  transition: transform 80ms;
}

.controles__meta {
  min-width: 0;
  flex: 1;
}

.controles__meta p {
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.controles__titulo {
  font-size: 15px;
  font-weight: 700;
}

.controles__detalle {
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  opacity: 0.8;
}

.controles__volumen {
  display: inline-flex;
  flex: none;
  align-items: center;
  gap: var(--space-2);
}

.controles__volumen input {
  width: 96px;
  accent-color: var(--accent2);
}
</style>
