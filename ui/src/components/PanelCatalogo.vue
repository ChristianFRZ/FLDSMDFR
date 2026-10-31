<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { ApiError } from '../api/http'
import * as songs from '../api/songs'
import type { SongOut } from '../api/types'
import { formatTime } from '../composables/formatTime'
import { usePlayer } from '../composables/usePlayer'
import BotonGrabar from './BotonGrabar.vue'
import AvisoEnLinea from './AvisoEnLinea.vue'

const ESPERA_MS = 250
const FILAS_ESQUELETO = 5

const player = usePlayer()

const busqueda = ref('')
// Texto de la búsqueda cuyos resultados se muestran (para el mensaje de vacío).
const buscado = ref('')
const canciones = ref<SongOut[]>([])
const total = ref(0)
const cargando = ref(true)
const cargandoMas = ref(false)
const error = ref('')

let temporizador: ReturnType<typeof setTimeout> | undefined
// Cada petición nueva invalida las anteriores: solo la última pinta resultados.
let peticion = 0

function mensajeDe(e: unknown): string {
  return e instanceof ApiError
    ? e.message
    : 'No pudimos cargar el catálogo. Revisa tu conexión y vuelve a intentarlo.'
}

async function buscar(): Promise<void> {
  const q = busqueda.value.trim()
  const mia = ++peticion
  cargando.value = true
  error.value = ''
  try {
    const pagina = await songs.list(q, 0)
    if (mia !== peticion) return
    canciones.value = pagina.items
    total.value = pagina.total
    buscado.value = q
  } catch (e) {
    if (mia !== peticion) return
    // Sin resultados viejos en pantalla: el error ocupa la lista y "Reintentar" repite la búsqueda.
    canciones.value = []
    total.value = 0
    error.value = mensajeDe(e)
  } finally {
    if (mia === peticion) cargando.value = false
  }
}

async function cargarMas(): Promise<void> {
  const mia = peticion
  cargandoMas.value = true
  error.value = ''
  try {
    const pagina = await songs.list(buscado.value, canciones.value.length)
    if (mia !== peticion) return
    canciones.value = [...canciones.value, ...pagina.items]
    total.value = pagina.total
  } catch (e) {
    if (mia === peticion) error.value = mensajeDe(e)
  } finally {
    cargandoMas.value = false
  }
}

function onInput(): void {
  clearTimeout(temporizador)
  temporizador = setTimeout(() => void buscar(), ESPERA_MS)
}

function reproducir(cancion: SongOut): void {
  void player.play(cancion, canciones.value)
}

onMounted(() => void buscar())
onBeforeUnmount(() => clearTimeout(temporizador))
</script>

<template>
  <section class="catalogo" aria-labelledby="titulo-catalogo">
    <h2 id="titulo-catalogo">Catálogo</h2>

    <div class="catalogo__buscador">
      <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
        <circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="currentColor" stroke-width="2" />
        <path d="M15.5 15.5L20 20" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
      </svg>
      <input
        v-model="busqueda"
        type="search"
        placeholder="Buscar canción, artista o álbum"
        aria-label="Buscar canción, artista o álbum"
        autocomplete="off"
        @input="onInput"
      />
    </div>

    <ul v-if="cargando" class="catalogo__lista" aria-label="Cargando canciones…">
      <li v-for="n in FILAS_ESQUELETO" :key="n" class="catalogo__esqueleto" aria-hidden="true">
        <span /><span />
      </li>
    </ul>

    <AvisoEnLinea v-else-if="error && canciones.length === 0" reintentar @reintentar="buscar">
      {{ error }}
    </AvisoEnLinea>

    <p v-else-if="canciones.length === 0" class="catalogo__vacio">
      {{
        buscado
          ? `No encontramos canciones con «${buscado}».`
          : 'Todavía no hay canciones en el catálogo.'
      }}
    </p>

    <template v-else>
      <ul class="catalogo__lista">
        <li v-for="cancion in canciones" :key="cancion.id" class="catalogo__fila">
          <button
            type="button"
            class="catalogo__reproducir"
            :aria-current="player.current.value?.id === cancion.id || undefined"
            @click="reproducir(cancion)"
          >
            <span class="catalogo__textos">
              <span class="catalogo__titulo" :title="cancion.title">{{ cancion.title }}</span>
              <span class="catalogo__detalle" :title="`${cancion.artist} · ${cancion.album}`">
                {{ cancion.artist }} · {{ cancion.album }}
              </span>
            </span>
            <span class="catalogo__duracion">{{ formatTime(cancion.duration_seconds) }}</span>
          </button>
          <BotonGrabar :song-id="cancion.id" :titulo="cancion.title" />
        </li>
      </ul>

      <AvisoEnLinea v-if="error" reintentar @reintentar="cargarMas">{{ error }}</AvisoEnLinea>

      <button
        v-if="canciones.length < total"
        type="button"
        class="catalogo__mas"
        :disabled="cargandoMas"
        :aria-busy="cargandoMas || undefined"
        @click="cargarMas"
      >
        {{ cargandoMas ? 'Cargando canciones…' : 'Cargar más' }}
      </button>
    </template>
  </section>
</template>

<style scoped>
.catalogo {
  display: grid;
  gap: var(--space-4);
  align-content: start;
}

.catalogo__buscador {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 44px;
  padding: 0 var(--space-4);
  border: 2px solid var(--ink);
  border-radius: 999px;
  background: var(--paper);
  color: var(--ink);
}

.catalogo__buscador svg {
  flex: none;
}

.catalogo__buscador input {
  flex: 1;
  min-width: 0;
  min-height: 40px;
  border: 0;
  background: transparent;
}

.catalogo__buscador input:focus-visible {
  outline: none;
  box-shadow: none;
}

/* El foco se dibuja en la píldora completa (anillo doble de base.css). */
.catalogo__buscador:focus-within {
  outline: 3px solid var(--accent2);
  outline-offset: 2px;
  box-shadow: 0 0 0 2px var(--ink);
}

.catalogo__buscador input::placeholder {
  color: var(--ink);
  opacity: 0.75;
}

.catalogo__lista {
  margin: 0;
  padding: 0;
  list-style: none;
}

.catalogo__fila {
  display: grid;
  grid-template-columns: 1fr 40px;
  align-items: center;
  gap: var(--space-3);
  border-bottom: 1px solid var(--rule);
}

.catalogo__reproducir {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
  min-height: 56px;
  padding: var(--space-2) var(--space-1);
  border: 0;
  border-radius: var(--radius-s);
  background: transparent;
  text-align: left;
}

@media (hover: hover) {
  .catalogo__reproducir:hover {
    background: color-mix(in srgb, currentColor 8%, transparent);
  }
}

.catalogo__reproducir[aria-current='true'] .catalogo__titulo {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.catalogo__textos {
  display: grid;
  min-width: 0;
}

.catalogo__titulo,
.catalogo__detalle {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.catalogo__titulo {
  font-weight: 700;
}

.catalogo__detalle,
.catalogo__duracion {
  font-size: 13px;
  opacity: 0.8;
}

.catalogo__duracion {
  font-variant-numeric: tabular-nums;
}

.catalogo__vacio {
  margin: 0;
}

.catalogo__esqueleto {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--rule);
}

.catalogo__esqueleto span {
  height: 12px;
  border-radius: var(--radius-s);
  background: var(--rule);
}

.catalogo__esqueleto span:first-child {
  width: 55%;
}

.catalogo__esqueleto span:last-child {
  width: 35%;
}

.catalogo__mas {
  justify-self: center;
  min-height: 40px;
  padding: 0 var(--space-5);
  border: 2px solid currentColor;
  border-radius: 999px;
  background: transparent;
  font-weight: 500;
}

@media (hover: hover) {
  .catalogo__mas:not(:disabled):hover {
    background: color-mix(in srgb, currentColor 12%, transparent);
  }
}
</style>
