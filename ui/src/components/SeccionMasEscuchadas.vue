<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import * as metrics from '../api/metrics'
import * as songs from '../api/songs'
import type { SongOut, TopSongOut } from '../api/types'
import { usePlayer } from '../composables/usePlayer'
import AvisoEnLinea from './AvisoEnLinea.vue'
import Portada from './Portada.vue'

// "Canciones más escuchadas" de la página de inicio (antes PanelTop).
const LIMITE = 5
const player = usePlayer()
const top = ref<TopSongOut[]>([])
const cargando = ref(true)
const error = ref(false)

// Solo se reproducen las que traen la canción completa (el top degradado no la trae).
const reproducibles = computed(() =>
  top.value.map((t) => t.song).filter((s): s is SongOut => !!s),
)

async function cargar(): Promise<void> {
  cargando.value = true
  error.value = false
  try {
    top.value = await metrics.top(LIMITE)
  } catch {
    error.value = true
  } finally {
    cargando.value = false
  }
}
onMounted(cargar)

function reproducir(t: TopSongOut): void {
  if (t.song) void player.play(t.song, reproducibles.value)
}

const veces = (n: number) => `${n} ${n === 1 ? 'reproducción' : 'reproducciones'}`
</script>

<template>
  <section class="tarjeta seccion" aria-labelledby="titulo-mas-escuchadas">
    <h2 id="titulo-mas-escuchadas" class="seccion__titulo">Canciones más escuchadas</h2>
    <div v-if="cargando" class="esqueleto-fila" aria-hidden="true"><span /><span /></div>
    <AvisoEnLinea v-else-if="error" reintentar @reintentar="cargar">
      No pudimos cargar las más escuchadas.
    </AvisoEnLinea>
    <p v-else-if="top.length === 0" class="texto-secundario">Todavía nadie escucha nada.</p>
    <ol v-else class="seccion__lista">
      <li v-for="(t, i) in top" :key="t.song_id">
        <button
          type="button"
          class="seccion__fila"
          :disabled="!t.song"
          :aria-label="`Reproducir «${t.title}» de ${t.artist}, ${veces(t.play_count)}`"
          @click="reproducir(t)"
        >
          <span class="seccion__puesto" aria-hidden="true">{{ i + 1 }}</span>
          <Portada
            :src="t.song?.has_cover ? songs.coverUrl(t.song_id) : null"
            :titulo="t.title"
            :tam="40"
          />
          <span class="seccion__texto">
            <span class="seccion__nombre">{{ t.title }}</span>
            <span class="seccion__detalle">{{ t.artist }} · {{ veces(t.play_count) }}</span>
          </span>
        </button>
      </li>
    </ol>
  </section>
</template>

<style scoped src="./seccion-inicio.css"></style>
