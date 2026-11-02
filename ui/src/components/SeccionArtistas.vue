<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import * as metrics from '../api/metrics'
import * as songs from '../api/songs'
import type { TopArtistOut } from '../api/types'
import AvisoEnLinea from './AvisoEnLinea.vue'
import Portada from './Portada.vue'

// "Artistas más escuchados": clic lleva al catálogo filtrado por el artista.
const LIMITE = 5
const artistas = ref<TopArtistOut[]>([])
const cargando = ref(true)
const error = ref(false)

async function cargar(): Promise<void> {
  cargando.value = true
  error.value = false
  try {
    artistas.value = await metrics.topArtists(LIMITE)
  } catch {
    error.value = true
  } finally {
    cargando.value = false
  }
}
onMounted(cargar)
</script>

<template>
  <section class="tarjeta seccion" aria-labelledby="titulo-artistas">
    <h2 id="titulo-artistas" class="seccion__titulo">Artistas más escuchados</h2>
    <div v-if="cargando" class="esqueleto-fila" aria-hidden="true"><span /><span /></div>
    <AvisoEnLinea v-else-if="error" reintentar @reintentar="cargar">
      No pudimos cargar los artistas.
    </AvisoEnLinea>
    <p v-else-if="artistas.length === 0" class="texto-secundario">Aún no hay artistas destacados.</p>
    <ol v-else class="seccion__lista">
      <li v-for="a in artistas" :key="a.artist">
        <RouterLink :to="{ path: '/catalogo', query: { q: a.artist } }" class="seccion__fila">
          <Portada
            :src="a.cover_song_id ? songs.coverUrl(a.cover_song_id) : null"
            :titulo="a.artist"
            :tam="40"
          />
          <span class="seccion__texto">
            <span class="seccion__nombre">{{ a.artist }}</span>
            <span class="seccion__detalle">
              {{ a.song_count }} {{ a.song_count === 1 ? 'tema' : 'temas' }} · {{ a.play_count }}
              {{ a.play_count === 1 ? 'reproducción' : 'reproducciones' }}
            </span>
          </span>
        </RouterLink>
      </li>
    </ol>
  </section>
</template>

<style scoped src="./seccion-inicio.css"></style>
