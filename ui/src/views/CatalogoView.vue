<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiError } from '../api/http'
import * as songs from '../api/songs'
import type { SongOut } from '../api/types'
import AvisoEnLinea from '../components/AvisoEnLinea.vue'
import FilaCancion from '../components/FilaCancion.vue'
import SelectorGrabar from '../components/SelectorGrabar.vue'
import Icono from '../components/icons/Icono.vue'
import { useBusqueda } from '../composables/useBusqueda'
import { usePlayer } from '../composables/usePlayer'
import { useSeguidos } from '../composables/useSeguidos'

// Catálogo: búsqueda sincronizada con ?q=, grabar en casetes y seguir artistas (DESIGN.md §8).
const MENSAJE_ERROR = 'No pudimos cargar el catálogo. Revisa tu conexión y vuelve a intentarlo.'
const FILAS_ESQUELETO = 5

const route = useRoute()
const router = useRouter()
const player = usePlayer()
const seguidos = useSeguidos()

const canciones = ref<SongOut[]>([])
const total = ref(0)
const cargandoMas = ref(false)
const errorMas = ref('')
const siguiendoOcupado = ref<string | null>(null)

const { busqueda, buscado, cargando, error, buscar, alEscribir, token, esVigente } = useBusqueda({
  consultar: (q: string) => songs.list(q, 0),
  aplicar: (pagina) => {
    canciones.value = pagina.items
    total.value = pagina.total
  },
  // Sin resultados viejos en pantalla: el error ocupa la lista y "Reintentar" repite la búsqueda.
  alFallar: () => {
    canciones.value = []
    total.value = 0
  },
  mensajeError: MENSAJE_ERROR,
})

const qDeRuta = () => (typeof route.query.q === 'string' ? route.query.q.trim() : '')

onMounted(() => {
  busqueda.value = qDeRuta()
  void buscar()
})

// El buscador del encabezado navega a /catalogo?q=…: si cambia por fuera, se busca de nuevo.
watch(qDeRuta, (q) => {
  if (q !== busqueda.value.trim()) {
    busqueda.value = q
    void buscar()
  }
})

// Lo buscado queda en la URL para compartirla o volver con "atrás".
watch(buscado, (q) => {
  if (q !== qDeRuta()) void router.replace({ query: q ? { ...route.query, q } : {} })
})

async function cargarMas(): Promise<void> {
  const mia = token()
  cargandoMas.value = true
  errorMas.value = ''
  try {
    const pagina = await songs.list(buscado.value, canciones.value.length)
    if (!esVigente(mia)) return
    canciones.value = [...canciones.value, ...pagina.items]
    total.value = pagina.total
  } catch (e) {
    if (esVigente(mia)) errorMas.value = e instanceof ApiError ? e.message : MENSAJE_ERROR
  } finally {
    cargandoMas.value = false
  }
}

const hayMas = computed(() => canciones.value.length < total.value)

// Resultados agrupados por artista (clave sin mayúsculas ni espacios), en orden de aparición.
const grupos = computed(() => {
  const mapa = new Map<string, { artista: string; canciones: SongOut[] }>()
  for (const c of canciones.value) {
    const clave = c.artist.trim().toLowerCase()
    const grupo = mapa.get(clave) ?? { artista: c.artist.trim(), canciones: [] }
    grupo.canciones.push(c)
    mapa.set(clave, grupo)
  }
  return [...mapa.values()]
})

function reproducir(cancion: SongOut): void {
  void player.play(cancion, canciones.value)
}

async function alternarSeguir(artista: string): Promise<void> {
  if (siguiendoOcupado.value) return
  siguiendoOcupado.value = artista
  try {
    await seguidos.alternar(artista)
  } finally {
    siguiendoOcupado.value = null
  }
}
</script>

<template>
  <section class="catalogo" aria-labelledby="titulo-catalogo">
    <header class="catalogo__cabecera">
      <p class="antetitulo">EXPLORA</p>
      <h1 id="titulo-catalogo">Catálogo</h1>
      <form class="busqueda-pildora catalogo__busqueda" role="search" @submit.prevent="buscar">
        <Icono nombre="search" :tam="18" />
        <label for="catalogo-busqueda" class="visualmente-oculto">Buscar canciones</label>
        <input
          id="catalogo-busqueda"
          v-model="busqueda"
          type="search"
          placeholder="Busca por título, artista o álbum"
          autocomplete="off"
          @input="alEscribir"
        />
      </form>
    </header>

    <div v-if="cargando" aria-hidden="true">
      <div v-for="n in FILAS_ESQUELETO" :key="n" class="esqueleto-fila"><span /><span /></div>
    </div>
    <AvisoEnLinea v-else-if="error" reintentar @reintentar="buscar">{{ error }}</AvisoEnLinea>
    <p v-else-if="canciones.length === 0" class="texto-secundario">
      <template v-if="buscado">No encontramos canciones con «{{ buscado }}».</template>
      <template v-else>Todavía no hay canciones en el catálogo.</template>
    </p>

    <template v-else>
      <p class="visualmente-oculto" aria-live="polite">{{ total }} canciones</p>
      <section
        v-for="g in grupos"
        :key="g.artista.toLowerCase()"
        class="catalogo__grupo"
        :aria-label="g.artista"
      >
        <header class="catalogo__artista">
          <h2 class="catalogo__nombre-artista">{{ g.artista }}</h2>
          <button
            type="button"
            class="boton-contorno"
            data-prueba="seguir"
            :aria-pressed="seguidos.sigue(g.artista)"
            :aria-label="`Seguir a ${g.artista}`"
            :disabled="siguiendoOcupado === g.artista"
            @click="alternarSeguir(g.artista)"
          >
            <template v-if="seguidos.sigue(g.artista)"><Icono nombre="check" :tam="14" />Siguiendo</template>
            <template v-else>Seguir</template>
          </button>
        </header>
        <ul class="catalogo__lista">
          <li v-for="c in g.canciones" :key="c.id">
            <FilaCancion
              :cancion="c"
              :sonando="player.current.value?.id === c.id"
              @reproducir="reproducir(c)"
            >
              <template #acciones>
                <SelectorGrabar :song-id="c.id" :titulo="c.title" />
              </template>
            </FilaCancion>
          </li>
        </ul>
      </section>

      <AvisoEnLinea v-if="errorMas" reintentar @reintentar="cargarMas">{{ errorMas }}</AvisoEnLinea>
      <button
        v-else-if="hayMas"
        type="button"
        class="boton-contorno catalogo__mas"
        :disabled="cargandoMas"
        :aria-busy="cargandoMas"
        @click="cargarMas"
      >
        {{ cargandoMas ? 'Cargando…' : 'Cargar más' }}
      </button>
    </template>
  </section>
</template>

<style scoped>
.catalogo {
  display: grid;
  gap: var(--space-5);
  padding: var(--space-5);
}

.catalogo__cabecera {
  display: grid;
  gap: var(--space-2);
}

.catalogo__busqueda {
  max-width: 480px;
  margin-top: var(--space-2);
}

.catalogo__grupo {
  display: grid;
  gap: var(--space-2);
}

.catalogo__artista {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--rule);
}

.catalogo__nombre-artista {
  font-size: 20px;
}

.catalogo__lista {
  display: grid;
  gap: var(--space-1);
  margin: 0;
  padding: 0;
  list-style: none;
}

.catalogo__mas {
  justify-self: center;
}

@media (max-width: 700px) {
  .catalogo {
    padding: var(--space-4);
  }
}
</style>
