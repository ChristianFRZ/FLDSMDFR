<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import * as songs from '../api/songs'
import { useFavoritos } from '../composables/useFavoritos'
import { usePlayer } from '../composables/usePlayer'
import BarraProgreso from './BarraProgreso.vue'
import ControlesTransporte from './ControlesTransporte.vue'
import { formatTime } from '../composables/formatTime'
import Portada from './Portada.vue'
import Icono from './icons/Icono.vue'

// Vista "Sonando ahora": pide pantalla completa; si el navegador la niega, queda como capa fija.
const emit = defineEmits<{ cerrar: [] }>()
const player = usePlayer()
const { current, currentTime, duration, buffered } = player
const favoritos = useFavoritos()

const raiz = ref<HTMLElement | null>(null)
const cerrarBoton = ref<HTMLButtonElement | null>(null)
const portada = computed(() =>
  current.value?.has_cover ? songs.coverUrl(current.value.id) : null,
)

function cerrar(): void {
  if (document.fullscreenElement) void document.exitFullscreen().catch(() => undefined)
  emit('cerrar')
}

// Esc dentro de pantalla completa lo atiende el navegador: al salir de ella se cierra la vista.
function onFullscreen(): void {
  if (!document.fullscreenElement) emit('cerrar')
}
function onKeydown(evento: KeyboardEvent): void {
  if (evento.key === 'Escape') cerrar()
}

onMounted(() => {
  document.addEventListener('keydown', onKeydown)
  cerrarBoton.value?.focus()
  const el = raiz.value
  if (el?.requestFullscreen) {
    el.requestFullscreen()
      .then(() => document.addEventListener('fullscreenchange', onFullscreen))
      .catch(() => undefined)
  }
})
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown)
  document.removeEventListener('fullscreenchange', onFullscreen)
  if (document.fullscreenElement === raiz.value) void document.exitFullscreen().catch(() => undefined)
})
</script>

<template>
  <div ref="raiz" class="sonando" role="dialog" aria-modal="true" aria-label="Sonando ahora">
    <button ref="cerrarBoton" type="button" class="boton-icono sonando__cerrar" aria-label="Salir de pantalla completa" @click="cerrar">
      <Icono nombre="minimize-2" :tam="22" />
    </button>

    <div v-if="current" class="sonando__contenido">
      <Portada :src="portada" :titulo="current.title" :tam="320" radio="m" />
      <div class="sonando__meta">
        <div>
          <h2 class="sonando__titulo">{{ current.title }}</h2>
          <p class="texto-secundario">{{ current.artist }}</p>
        </div>
        <button
          type="button"
          class="boton-icono"
          :aria-label="favoritos.esFavorita(current.id) ? 'Quitar de favoritas' : 'Añadir a favoritas'"
          :aria-pressed="favoritos.esFavorita(current.id)"
          @click="favoritos.alternar(current.id)"
        >
          <Icono nombre="heart" :tam="24" :class="{ 'sonando__corazon--lleno': favoritos.esFavorita(current.id) }" />
        </button>
      </div>
      <div class="sonando__progreso">
        <span class="texto-secundario">{{ formatTime(currentTime) }}</span>
        <BarraProgreso :current-time="currentTime" :duration="duration" :buffered="buffered" @seek="player.seek" />
        <span class="texto-secundario">{{ formatTime(duration) }}</span>
      </div>
      <ControlesTransporte grande />
    </div>
    <p v-else class="texto-secundario">Elige una canción para empezar.</p>
  </div>
</template>

<style scoped>
.sonando {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: grid;
  place-items: center;
  padding: var(--space-6) var(--space-4);
  overflow-y: auto;
  background: var(--bg);
}

.sonando__cerrar {
  position: absolute;
  top: var(--space-4);
  right: var(--space-4);
}

.sonando__contenido {
  display: grid;
  gap: var(--space-5);
  width: min(420px, 100%);
  justify-items: center;
}

.sonando__contenido > :deep(.portada) {
  width: min(320px, 70vw) !important;
  height: min(320px, 70vw) !important;
}

.sonando__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  width: 100%;
}

.sonando__titulo {
  font-size: 28px;
}

.sonando__progreso {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: var(--space-3);
  width: 100%;
  font-variant-numeric: tabular-nums;
}

.sonando__corazon--lleno {
  fill: currentColor;
}
</style>
