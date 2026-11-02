<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import * as playlists from '../api/playlists'
import * as songs from '../api/songs'
import type { PlaylistSummary } from '../api/types'
import { useCasetes } from '../composables/useCasetes'
import { useFavoritos } from '../composables/useFavoritos'
import { useSeguidos } from '../composables/useSeguidos'
import CampoCaseteNuevo from './CampoCaseteNuevo.vue'
import Portada from './Portada.vue'
import Icono from './icons/Icono.vue'

// Biblioteca de la barra lateral: casetes y artistas seguidos (DESIGN.md §7.2).
type Pestana = 'casetes' | 'artistas'
const PESTANAS: ReadonlyArray<{ id: Pestana; texto: string }> = [
  { id: 'casetes', texto: 'Casetes' },
  { id: 'artistas', texto: 'Artistas' },
]

const router = useRouter()
const { casetes, error } = useCasetes()
const favoritos = useFavoritos()
const seguidos = useSeguidos()

const pestana = ref<Pestana>('casetes')
const creando = ref(false)

// App los carga al entrar; la vista móvil puede montarse antes de que lleguen.
onMounted(() => {
  if (seguidos.artistas.value.length === 0) void seguidos.cargar()
})

const canciones = (n: number) => `${n} ${n === 1 ? 'canción' : 'canciones'}`
const detalle = (c: PlaylistSummary) =>
  c.role === 'collaborator' ? 'Casete · Colaborativo' : `Casete · ${canciones(c.song_count)}`

function moverPestana(evento: KeyboardEvent): void {
  const actual = PESTANAS.findIndex((p) => p.id === pestana.value)
  let destino = actual
  if (evento.key === 'ArrowRight') destino = (actual + 1) % PESTANAS.length
  else if (evento.key === 'ArrowLeft') destino = (actual - 1 + PESTANAS.length) % PESTANAS.length
  else if (evento.key === 'Home') destino = 0
  else if (evento.key === 'End') destino = PESTANAS.length - 1
  else return
  evento.preventDefault()
  pestana.value = PESTANAS[destino].id
  void nextTick(() => document.getElementById(`pestana-${PESTANAS[destino].id}`)?.focus())
}

async function onCreado(nuevo: PlaylistSummary): Promise<void> {
  creando.value = false
  pestana.value = 'casetes'
  await router.push(`/casete/${nuevo.id}`)
}
</script>

<template>
  <section class="biblioteca" aria-labelledby="titulo-biblioteca">
    <header class="biblioteca__cabecera">
      <h2 id="titulo-biblioteca" class="antetitulo">TUS CASETES</h2>
      <button
        type="button"
        class="boton-icono"
        aria-label="Crear casete"
        :aria-expanded="creando"
        @click="creando = !creando"
      >
        <Icono nombre="plus" :tam="18" />
      </button>
    </header>

    <CampoCaseteNuevo v-if="creando" @creado="onCreado" @cancelar="creando = false" />

    <div class="biblioteca__pestanas" role="tablist" aria-label="Biblioteca" @keydown="moverPestana">
      <button
        v-for="p in PESTANAS"
        :id="`pestana-${p.id}`"
        :key="p.id"
        type="button"
        role="tab"
        class="pastilla"
        :aria-selected="pestana === p.id"
        :aria-controls="`panel-${p.id}`"
        :tabindex="pestana === p.id ? 0 : -1"
        @click="pestana = p.id"
      >
        {{ p.texto }}
      </button>
    </div>

    <div
      v-if="pestana === 'casetes'"
      id="panel-casetes"
      role="tabpanel"
      aria-labelledby="pestana-casetes"
    >
      <ul class="biblioteca__lista">
        <li>
          <RouterLink to="/favoritas" class="biblioteca__fila" data-prueba="fila-biblioteca" active-class="biblioteca__fila--activa">
            <span class="biblioteca__favoritas" aria-hidden="true"><Icono nombre="heart" :tam="18" /></span>
            <span class="biblioteca__texto">
              <span class="biblioteca__nombre">Tus favoritas</span>
              <span class="biblioteca__detalle">Casete · {{ canciones(favoritos.ids.value.size) }}</span>
            </span>
          </RouterLink>
        </li>
        <li v-for="c in casetes" :key="c.id">
          <RouterLink
            :to="`/casete/${c.id}`"
            class="biblioteca__fila"
            data-prueba="fila-biblioteca"
            active-class="biblioteca__fila--activa"
          >
            <Portada :src="c.has_cover ? playlists.coverUrl(c.id) : null" :titulo="c.name" :tam="42" />
            <span class="biblioteca__texto">
              <span class="biblioteca__nombre">{{ c.name }}</span>
              <span class="biblioteca__detalle">{{ detalle(c) }}</span>
            </span>
          </RouterLink>
        </li>
      </ul>
      <p v-if="error" class="biblioteca__vacio">{{ error }}</p>
      <p v-else-if="casetes.length === 0" class="biblioteca__vacio">
        Aún no tienes casetes. Crea uno con +.
      </p>
    </div>

    <div v-else id="panel-artistas" role="tabpanel" aria-labelledby="pestana-artistas">
      <ul v-if="seguidos.artistas.value.length" class="biblioteca__lista">
        <li v-for="a in seguidos.artistas.value" :key="a.artist">
          <RouterLink
            :to="{ path: '/catalogo', query: { q: a.artist } }"
            class="biblioteca__fila"
            data-prueba="fila-biblioteca"
          >
            <Portada
              :src="a.cover_song_id ? songs.coverUrl(a.cover_song_id) : null"
              :titulo="a.artist"
              :tam="42"
            />
            <span class="biblioteca__texto">
              <span class="biblioteca__nombre">{{ a.artist }}</span>
              <span class="biblioteca__detalle">Artista · {{ a.song_count }} {{ a.song_count === 1 ? 'tema' : 'temas' }}</span>
            </span>
          </RouterLink>
        </li>
      </ul>
      <p v-else class="biblioteca__vacio">Sigue artistas desde el catálogo para verlos aquí.</p>
    </div>
  </section>
</template>

<style scoped>
.biblioteca {
  display: grid;
  gap: var(--space-3);
}

.biblioteca__cabecera {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.biblioteca__pestanas {
  display: flex;
  gap: var(--space-2);
}

.biblioteca__lista {
  display: grid;
  gap: var(--space-1);
  margin: 0;
  padding: 0;
  list-style: none;
}

.biblioteca__fila {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-1);
  border-radius: var(--radius-m);
  color: var(--ink);
  text-decoration: none;
}

@media (hover: hover) {
  .biblioteca__fila:hover {
    background: color-mix(in srgb, var(--surface) 45%, transparent);
  }
}

.biblioteca__fila--activa {
  background: var(--surface-active);
  color: var(--ink-on-active);
}

.biblioteca__fila--activa .biblioteca__detalle {
  color: var(--ink-on-active);
}

.biblioteca__favoritas {
  display: grid;
  flex-shrink: 0;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: var(--radius-s);
  background: var(--accent);
  color: var(--on-accent);
}

.biblioteca__favoritas :deep(.icono) {
  fill: currentColor;
}

.biblioteca__texto {
  display: grid;
  min-width: 0;
}

.biblioteca__nombre,
.biblioteca__detalle {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.biblioteca__nombre {
  font-size: 12px;
  font-weight: 600;
}

.biblioteca__detalle {
  color: var(--ink-muted);
  font-size: 10px;
}

.biblioteca__vacio {
  padding: var(--space-2) 0;
  color: var(--ink-muted);
  font-size: 12px;
}
</style>
