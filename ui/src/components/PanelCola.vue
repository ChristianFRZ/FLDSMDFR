<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'
import * as songs from '../api/songs'
import { formatTime } from '../composables/formatTime'
import { usePlayer } from '../composables/usePlayer'
import Portada from './Portada.vue'
import Icono from './icons/Icono.vue'

// Panel lateral derecho con lo que sigue en la cola; reordenar y quitar (DESIGN.md §7.7).
const emit = defineEmits<{ cerrar: [] }>()
const player = usePlayer()
const { current, upcoming } = player

function onKeydown(evento: KeyboardEvent): void {
  if (evento.key === 'Escape') emit('cerrar')
}
onMounted(() => document.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))
</script>

<template>
  <aside class="cola" aria-labelledby="titulo-cola">
    <header class="cola__cabecera">
      <h2 id="titulo-cola" class="cola__titulo">Cola</h2>
      <button type="button" class="boton-icono" aria-label="Cerrar cola" @click="emit('cerrar')">
        <Icono nombre="x" :tam="18" />
      </button>
    </header>

    <template v-if="current">
      <p class="antetitulo">Sonando</p>
      <div class="cola__fila cola__fila--actual">
        <Portada :src="current.has_cover ? songs.coverUrl(current.id) : null" :titulo="current.title" :tam="40" />
        <div class="cola__texto">
          <p class="cola__nombre">{{ current.title }}</p>
          <p class="texto-secundario">{{ current.artist }}</p>
        </div>
      </div>
    </template>

    <p class="antetitulo">A continuación</p>
    <p v-if="upcoming.length === 0" class="texto-secundario">No hay más canciones en la cola.</p>
    <ol v-else class="cola__lista">
      <li v-for="(cancion, i) in upcoming" :key="cancion.id" class="cola__fila" data-prueba="fila-cola">
        <Portada :src="cancion.has_cover ? songs.coverUrl(cancion.id) : null" :titulo="cancion.title" :tam="40" />
        <div class="cola__texto">
          <p class="cola__nombre">{{ cancion.title }}</p>
          <p class="texto-secundario">{{ cancion.artist }} · {{ formatTime(cancion.duration_seconds) }}</p>
        </div>
        <div class="cola__acciones">
          <button
            type="button"
            class="boton-icono"
            :aria-label="`Subir «${cancion.title}»`"
            :disabled="i === 0"
            @click="player.moveInQueue(i, i - 1)"
          >
            <Icono nombre="arrow-up" :tam="16" />
          </button>
          <button
            type="button"
            class="boton-icono"
            :aria-label="`Bajar «${cancion.title}»`"
            :disabled="i === upcoming.length - 1"
            @click="player.moveInQueue(i, i + 1)"
          >
            <Icono nombre="arrow-down" :tam="16" />
          </button>
          <button
            type="button"
            class="boton-icono"
            :aria-label="`Quitar «${cancion.title}» de la cola`"
            @click="player.removeFromQueue(i)"
          >
            <Icono nombre="x" :tam="16" />
          </button>
        </div>
      </li>
    </ol>
  </aside>
</template>

<style scoped>
.cola {
  position: fixed;
  top: 0;
  right: 0;
  bottom: var(--player-height);
  z-index: 30;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  width: min(360px, 100vw);
  padding: var(--space-4);
  overflow-y: auto;
  border-left: 1px solid var(--surface);
  background: var(--bg);
}

.cola__cabecera {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.cola__titulo {
  font-size: 20px;
}

.cola__lista {
  display: grid;
  gap: var(--space-1);
  margin: 0;
  padding: 0;
  list-style: none;
}

.cola__fila {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-1);
  border-radius: var(--radius-m);
}

.cola__fila--actual {
  background: var(--surface-active);
  color: var(--ink-on-active);
}

.cola__fila--actual .texto-secundario {
  color: var(--ink-on-active);
}

.cola__texto {
  flex: 1;
  min-width: 0;
}

.cola__nombre {
  overflow: hidden;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cola__acciones {
  display: flex;
}
</style>
