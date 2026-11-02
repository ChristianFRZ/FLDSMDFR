<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import * as songs from '../api/songs'
import { formatTime } from '../composables/formatTime'
import { useFavoritos } from '../composables/useFavoritos'
import { usePlayer } from '../composables/usePlayer'
import BarraProgreso from './BarraProgreso.vue'
import ControlesTransporte from './ControlesTransporte.vue'
import PanelCola from './PanelCola.vue'
import Portada from './Portada.vue'
import SonandoAhora from './SonandoAhora.vue'
import Icono from './icons/Icono.vue'

// Barra fija del reproductor (DESIGN.md §7.4).
const player = usePlayer()
const { current, currentTime, duration, buffered, volume } = player
const favoritos = useFavoritos()

const colaAbierta = ref(false)
const pantallaCompleta = ref(false)
let volumenPrevio = 1

const portada = computed(() =>
  current.value?.has_cover ? songs.coverUrl(current.value.id) : null,
)
const favorita = computed(() => !!current.value && favoritos.esFavorita(current.value.id))
const silenciado = computed(() => volume.value === 0)
const volumenPorcentaje = computed(() => Math.round(volume.value * 100))

function onVolumen(evento: Event): void {
  player.setVolume(Number((evento.target as HTMLInputElement).value) / 100)
}

function alternarSilencio(): void {
  if (silenciado.value) player.setVolume(volumenPrevio || 1)
  else {
    volumenPrevio = volume.value
    player.setVolume(0)
  }
}

// La barra espaciadora reproduce/pausa salvo cuando el foco está en algo que la usa.
function usaEspacio(objetivo: EventTarget | null): boolean {
  if (!(objetivo instanceof HTMLElement)) return false
  if (objetivo.isContentEditable) return true
  return ['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON', 'A'].includes(objetivo.tagName)
    || objetivo.getAttribute('role') === 'slider'
}

function onKeydown(evento: KeyboardEvent): void {
  if (evento.key !== ' ' || evento.ctrlKey || evento.metaKey || evento.altKey) return
  if (evento.defaultPrevented || usaEspacio(evento.target)) return
  evento.preventDefault()
  player.toggle()
}

onMounted(() => document.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))
</script>

<template>
  <section class="reproductor" aria-label="Reproductor">
    <div class="reproductor__cancion">
      <template v-if="current">
        <Portada :src="portada" :titulo="current.title" :tam="58" />
        <div class="reproductor__texto">
          <p class="reproductor__titulo">{{ current.title }}</p>
          <p class="texto-secundario reproductor__artista">{{ current.artist }}</p>
        </div>
        <button
          type="button"
          class="boton-icono"
          :class="{ 'reproductor__corazon--lleno': favorita }"
          :aria-label="favorita ? 'Quitar de favoritas' : 'Añadir a favoritas'"
          :aria-pressed="favorita"
          @click="favoritos.alternar(current.id)"
        >
          <Icono nombre="heart" :tam="18" />
        </button>
      </template>
      <p v-else class="texto-secundario">Elige una canción para empezar.</p>
    </div>

    <div class="reproductor__centro">
      <ControlesTransporte />
      <div class="reproductor__progreso">
        <span class="reproductor__tiempo">{{ formatTime(currentTime) }}</span>
        <BarraProgreso :current-time="currentTime" :duration="duration" :buffered="buffered" @seek="player.seek" />
        <span class="reproductor__tiempo">{{ formatTime(duration) }}</span>
      </div>
    </div>

    <div class="reproductor__herramientas">
      <button type="button" class="boton-icono" aria-label="Letras (próximamente)" aria-disabled="true" title="Próximamente">
        <Icono nombre="mic-2" :tam="16" />
      </button>
      <button type="button" class="boton-icono" aria-label="Dispositivos (próximamente)" aria-disabled="true" title="Próximamente">
        <Icono nombre="monitor-speaker" :tam="16" />
      </button>
      <button
        type="button"
        class="boton-icono"
        aria-label="Cola de reproducción"
        :aria-expanded="colaAbierta"
        @click="colaAbierta = !colaAbierta"
      >
        <Icono nombre="list-music" :tam="16" />
      </button>
      <div class="reproductor__volumen">
        <button
          type="button"
          class="boton-icono"
          :aria-label="silenciado ? 'Activar sonido' : 'Silenciar'"
          @click="alternarSilencio"
        >
          <Icono :nombre="silenciado ? 'volume-x' : 'volume-2'" :tam="16" />
        </button>
        <input
          type="range"
          min="0"
          max="100"
          step="1"
          aria-label="Volumen"
          :value="volumenPorcentaje"
          :aria-valuetext="`${volumenPorcentaje} %`"
          @input="onVolumen"
        />
      </div>
      <button
        type="button"
        class="boton-icono"
        aria-label="Pantalla completa"
        :disabled="!current"
        @click="pantallaCompleta = true"
      >
        <Icono nombre="maximize-2" :tam="16" />
      </button>
    </div>

    <PanelCola v-if="colaAbierta" @cerrar="colaAbierta = false" />
    <SonandoAhora v-if="pantallaCompleta" @cerrar="pantallaCompleta = false" />
  </section>
</template>

<style scoped>
.reproductor {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 2fr) minmax(0, 1fr);
  align-items: center;
  gap: var(--space-4);
  height: 100%;
  padding: 0 var(--space-4);
  border-top: 1px solid var(--surface);
  background: var(--bg);
}

.reproductor__cancion {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
}

.reproductor__texto {
  min-width: 0;
}

.reproductor__titulo,
.reproductor__artista {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.reproductor__titulo {
  font-weight: 600;
}

.reproductor__artista {
  font-size: 11px;
}

.reproductor__corazon--lleno :deep(.icono) {
  fill: currentColor;
}

.reproductor__centro {
  display: grid;
  gap: var(--space-1);
  max-width: 560px;
  width: 100%;
  justify-self: center;
}

.reproductor__progreso {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: var(--space-2);
}

.reproductor__tiempo {
  min-width: 34px;
  color: var(--ink-muted);
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  text-align: center;
}

.reproductor__herramientas {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-1);
}

.reproductor__volumen {
  display: flex;
  align-items: center;
}

.reproductor__volumen input {
  width: 88px;
  accent-color: var(--accent);
}

/* En pantallas estrechas solo quedan canción y transporte. */
@media (max-width: 900px) {
  .reproductor {
    grid-template-columns: minmax(0, 1fr) auto;
    padding: 0 var(--space-3);
  }

  .reproductor__progreso,
  .reproductor__herramientas > :not([aria-label='Cola de reproducción']) {
    display: none;
  }
}
</style>
