<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import * as me from '../api/me'
import type { FavoritesOut } from '../api/types'
import AvisoEnLinea from '../components/AvisoEnLinea.vue'
import CabeceraCasete from '../components/CabeceraCasete.vue'
import FilaCancion from '../components/FilaCancion.vue'
import Icono from '../components/icons/Icono.vue'
import { AVISO_DEGRADADO, desdeFavorita, resumenDuracion } from '../composables/canciones'
import { useFavoritos } from '../composables/useFavoritos'
import { usePlayer } from '../composables/usePlayer'

// "Tus favoritas": como un casete, sin nombre, portada ni compartir editables.
const player = usePlayer()
const favoritos = useFavoritos()

const datos = ref<FavoritesOut | null>(null)
const cargando = ref(true)
const error = ref(false)

const canciones = computed(() => datos.value?.songs.map(desdeFavorita) ?? [])
const reproducibles = computed(() => canciones.value.filter((c) => c.is_active))
const detalle = computed(() =>
  resumenDuracion(datos.value?.songs.length ?? 0, datos.value?.total_seconds ?? 0),
)

async function cargar(): Promise<void> {
  cargando.value = true
  error.value = false
  try {
    datos.value = await me.favorites()
  } catch {
    error.value = true
  } finally {
    cargando.value = false
  }
}
onMounted(cargar)
// Un corazón cambiado en cualquier sitio (reproductor, menú) recarga la lista.
watch(favoritos.version, cargar)

function reproducirTodo(): void {
  const [primera] = reproducibles.value
  if (primera) void player.play(primera, reproducibles.value)
}

function reproducir(i: number): void {
  const cancion = canciones.value[i]
  if (cancion?.is_active) void player.play(cancion, reproducibles.value)
}
</script>

<template>
  <section class="favoritas" aria-labelledby="titulo-favoritas">
    <CabeceraCasete antetitulo="CASETE" :detalle="detalle">
      <template #portada>
        <span class="favoritas__portada" aria-hidden="true"><Icono nombre="heart" :tam="64" /></span>
      </template>
      <template #titulo><h1 id="titulo-favoritas">Tus favoritas</h1></template>
      <template #acciones>
        <button
          type="button"
          class="boton-principal"
          :disabled="reproducibles.length === 0"
          @click="reproducirTodo"
        >
          <Icono nombre="play" :tam="14" /> Reproducir todo
        </button>
      </template>
    </CabeceraCasete>

    <AvisoEnLinea v-if="datos?.degraded && !error" tipo="aviso">{{ AVISO_DEGRADADO }}</AvisoEnLinea>
    <div v-if="cargando && !datos" class="esqueleto-fila" aria-hidden="true"><span /><span /></div>
    <AvisoEnLinea v-else-if="error" reintentar @reintentar="cargar">
      No pudimos cargar tus favoritas.
    </AvisoEnLinea>
    <p v-else-if="canciones.length === 0" class="texto-secundario">
      Marca canciones con el corazón para tenerlas aquí. Empieza en el
      <RouterLink to="/catalogo">Catálogo</RouterLink>.
    </p>
    <ol v-else class="favoritas__lista">
      <li v-for="(c, i) in canciones" :key="c.id">
        <FilaCancion
          :cancion="c"
          :estado="datos?.songs[i]?.status"
          :sonando="player.current.value?.id === c.id"
          @reproducir="reproducir(i)"
        />
      </li>
    </ol>
  </section>
</template>

<style scoped>
.favoritas {
  display: grid;
  gap: var(--space-5);
  padding: var(--space-5);
}

.favoritas__portada {
  display: grid;
  place-items: center;
  width: 160px;
  height: 160px;
  border-radius: var(--radius-m);
  background: var(--accent);
  color: var(--on-accent);
}

.favoritas__portada :deep(.icono) {
  fill: currentColor;
}

.favoritas__lista {
  display: grid;
  gap: var(--space-1);
  margin: 0;
  padding: 0;
  list-style: none;
}

@media (max-width: 700px) {
  .favoritas {
    padding: var(--space-4);
  }
}
</style>
