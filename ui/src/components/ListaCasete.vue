<script setup lang="ts">
import { computed } from 'vue'
import type { PlaylistSongOut, SongOut } from '../api/types'
import { formatTime } from '../composables/formatTime'
import { useCasetes } from '../composables/useCasetes'
import { usePlayer } from '../composables/usePlayer'
import AvisoEnLinea from './AvisoEnLinea.vue'

const { activo, cargando, error, cargar, quitar, mover } = useCasetes()
const player = usePlayer()

const canciones = computed(() => activo.value?.songs ?? [])
const hayDegradadas = computed(() => canciones.value.some((s) => s.status === 'degraded'))
const pie = computed(() => {
  const n = canciones.value.length
  const total = formatTime(activo.value?.total_seconds ?? 0)
  return `${n} ${n === 1 ? 'canción' : 'canciones'} · ${total}`
})

function aCancion(s: PlaylistSongOut): SongOut {
  return {
    id: s.song_id,
    title: s.title,
    artist: s.artist,
    album: s.album,
    duration_seconds: s.duration_seconds,
    is_active: true,
    has_cover: false,
  }
}

function reproducir(fila: PlaylistSongOut): void {
  if (fila.status === 'unavailable') return
  const cola = canciones.value.filter((s) => s.status !== 'unavailable').map(aCancion)
  const inicio = cola.find((s) => s.id === fila.song_id)
  if (inicio) void player.play(inicio, cola)
}

const suena = (fila: PlaylistSongOut) => player.current.value?.id === fila.song_id
</script>

<template>
  <section class="lista-casete" aria-label="Canciones del casete">
    <ul v-if="cargando && !activo" class="lista-casete__filas" aria-label="Cargando canciones…">
      <li v-for="n in 3" :key="n" class="lista-casete__esqueleto" aria-hidden="true"><span /></li>
    </ul>

    <AvisoEnLinea v-else-if="error && !activo" reintentar @reintentar="cargar">{{ error }}</AvisoEnLinea>

    <template v-else-if="activo">
      <AvisoEnLinea v-if="hayDegradadas" tipo="aviso">
        Mostramos la última versión guardada; algunos datos pueden estar desactualizados.
      </AvisoEnLinea>

      <p v-if="canciones.length === 0" class="lista-casete__vacio">
        Este casete está vacío. Busca una canción y pulsa + para grabarla.
      </p>

      <ol v-else class="lista-casete__filas">
        <li
          v-for="(fila, i) in canciones"
          :key="fila.song_id"
          class="lista-casete__fila"
          :class="{
            'lista-casete__fila--suena': suena(fila),
            'lista-casete__fila--no-disponible': fila.status === 'unavailable',
          }"
        >
          <span v-if="fila.status === 'unavailable'" class="lista-casete__principal">
            <span class="lista-casete__marca" aria-hidden="true" />
            <span class="lista-casete__textos">
              <span class="lista-casete__titulo" :title="fila.title">{{ fila.title }}</span>
              <span class="lista-casete__estado">No disponible</span>
            </span>
            <span class="lista-casete__duracion">{{ formatTime(fila.duration_seconds) }}</span>
          </span>
          <button
            v-else
            type="button"
            class="lista-casete__principal"
            :aria-current="suena(fila) || undefined"
            @click="reproducir(fila)"
          >
            <span class="lista-casete__marca" aria-hidden="true">
              <svg v-if="suena(fila)" viewBox="0 0 24 24" width="14" height="14">
                <path d="M7 4l13 8-13 8z" fill="currentColor" />
              </svg>
            </span>
            <span class="lista-casete__textos">
              <span class="lista-casete__titulo" :title="fila.title">{{ fila.title }}</span>
              <span
                v-if="fila.status === 'degraded'"
                class="lista-casete__estado"
                title="El catálogo no respondió; mostramos los datos que guardamos al grabarla."
              >
                Datos guardados
              </span>
            </span>
            <span class="lista-casete__duracion">{{ formatTime(fila.duration_seconds) }}</span>
          </button>

          <span class="lista-casete__acciones">
            <button
              type="button"
              class="boton-icono"
              :aria-label="`Subir «${fila.title}»`"
              :disabled="i === 0"
              @click="mover(fila.song_id, -1)"
            >
              <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
                <path d="M6 15l6-6 6 6" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </button>
            <button
              type="button"
              class="boton-icono"
              :aria-label="`Bajar «${fila.title}»`"
              :disabled="i === canciones.length - 1"
              @click="mover(fila.song_id, 1)"
            >
              <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
                <path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </button>
            <button
              type="button"
              class="boton-icono"
              :aria-label="`Quitar «${fila.title}» del casete`"
              @click="quitar(fila.song_id)"
            >
              <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
                <path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" />
              </svg>
            </button>
          </span>
        </li>
      </ol>

      <p v-if="canciones.length > 0" class="lista-casete__pie">{{ pie }}</p>
    </template>
  </section>
</template>

<style scoped>
.lista-casete {
  display: grid;
  gap: var(--space-3);
  align-content: start;
  color: var(--deck-ink);
}

.lista-casete__filas {
  margin: 0;
  padding: 0;
  list-style: none;
}

.lista-casete__fila {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 44px;
  border-bottom: 1px solid var(--rule-deck);
}

.lista-casete__fila--suena::before {
  position: absolute;
  top: var(--space-1);
  bottom: var(--space-1);
  left: 0;
  width: 3px;
  border-radius: 2px;
  background: var(--accent2);
  content: '';
}

.lista-casete__principal {
  display: flex;
  flex: 1;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
  min-height: 44px;
  padding: var(--space-1) var(--space-2);
  border: 0;
  border-radius: var(--radius-s);
  background: transparent;
  color: var(--deck-ink);
  text-align: left;
}

@media (hover: hover) {
  button.lista-casete__principal:hover {
    background: color-mix(in srgb, currentColor 10%, transparent);
  }
}

.lista-casete__fila--no-disponible .lista-casete__principal {
  opacity: 0.6;
  cursor: default;
}

.lista-casete__marca {
  display: inline-flex;
  flex: none;
  width: 14px;
  color: var(--accent2);
}

.lista-casete__textos {
  display: grid;
  flex: 1;
  min-width: 0;
}

.lista-casete__titulo {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.lista-casete__fila--suena .lista-casete__titulo {
  font-weight: 700;
}

.lista-casete__estado,
.lista-casete__duracion,
.lista-casete__pie {
  font-size: 13px;
  opacity: 0.8;
}

.lista-casete__duracion,
.lista-casete__pie {
  font-variant-numeric: tabular-nums;
}

.lista-casete__duracion {
  flex: none;
}

.lista-casete__acciones {
  display: inline-flex;
  flex: none;
  gap: var(--space-2);
}

/* Con ratón, las acciones aparecen al pasar o enfocar la fila; en táctil siempre se ven. */
@media (hover: hover) {
  .lista-casete__acciones {
    opacity: 0;
  }

  .lista-casete__fila:hover .lista-casete__acciones,
  .lista-casete__fila:focus-within .lista-casete__acciones {
    opacity: 1;
  }
}

.boton-icono {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  padding: 0;
  border: 2px solid currentColor;
  border-radius: 50%;
  background: transparent;
  color: var(--deck-ink);
}

@media (hover: hover) {
  .boton-icono:not(:disabled):hover {
    background: color-mix(in srgb, currentColor 12%, transparent);
  }
}

.lista-casete__vacio,
.lista-casete__pie {
  margin: 0;
}

.lista-casete__esqueleto {
  padding: var(--space-4) var(--space-2);
  border-bottom: 1px solid var(--rule-deck);
}

.lista-casete__esqueleto span {
  display: block;
  width: 60%;
  height: 12px;
  border-radius: var(--radius-s);
  background: var(--rule-deck);
}
</style>
