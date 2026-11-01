<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import * as me from '../api/me'
import type { HistoryItemOut, PlaylistSummary } from '../api/types'
import AvisoEnLinea from '../components/AvisoEnLinea.vue'
import CampoCaseteNuevo from '../components/CampoCaseteNuevo.vue'
import FilaCancion from '../components/FilaCancion.vue'
import SeccionArtistas from '../components/SeccionArtistas.vue'
import SeccionMasEscuchadas from '../components/SeccionMasEscuchadas.vue'
import TarjetaAviso from '../components/TarjetaAviso.vue'
import Icono from '../components/icons/Icono.vue'
import { saludo } from '../composables/saludo'
import { useNotificaciones } from '../composables/useNotificaciones'
import { usePlayer } from '../composables/usePlayer'
import { useSession } from '../composables/useSession'

// Página de inicio (DESIGN.md §8).
const RECIENTES = 6
const AVISOS_VISIBLES = 2

const router = useRouter()
const { user } = useSession()
const player = usePlayer()
const notificaciones = useNotificaciones()

const titulo = computed(() => saludo(new Date(), user.value?.name ?? ''))
const avisos = computed(() => notificaciones.items.value.slice(0, AVISOS_VISIBLES))

const recientes = ref<HistoryItemOut[]>([])
const cargandoRecientes = ref(true)
const errorRecientes = ref(false)
const creando = ref(false)

const disponibles = computed(() => recientes.value.filter((h) => h.available).map((h) => h.song))

async function cargarRecientes(): Promise<void> {
  cargandoRecientes.value = true
  errorRecientes.value = false
  try {
    recientes.value = (await me.history(RECIENTES)).items
  } catch {
    errorRecientes.value = true
  } finally {
    cargandoRecientes.value = false
  }
}
onMounted(cargarRecientes)

function reproducir(item: HistoryItemOut): void {
  if (item.available) void player.play(item.song, disponibles.value)
}

async function onCreado(nuevo: PlaylistSummary): Promise<void> {
  creando.value = false
  await router.push(`/casete/${nuevo.id}`)
}
</script>

<template>
  <section class="inicio" aria-labelledby="titulo-inicio">
    <header class="inicio__cabecera">
      <p class="antetitulo">TU CASETERA DIARIA</p>
      <h1 id="titulo-inicio">{{ titulo }}</h1>
    </header>

    <div class="inicio__columnas">
      <SeccionMasEscuchadas />
      <SeccionArtistas />
      <div class="inicio__apiladas">
        <section class="tarjeta inicio__crear" aria-labelledby="titulo-crear">
          <h2 id="titulo-crear" class="inicio__subtitulo">Crear casete</h2>
          <p class="texto-secundario">Junta tus canciones en un casete nuevo y compártelo.</p>
          <CampoCaseteNuevo v-if="creando" @creado="onCreado" @cancelar="creando = false" />
          <button v-else type="button" class="boton-principal" @click="creando = true">
            <Icono nombre="plus" :tam="16" /> Nuevo casete
          </button>
        </section>

        <section class="tarjeta inicio__avisos" aria-labelledby="titulo-avisos">
          <h2 id="titulo-avisos" class="inicio__subtitulo">
            Avisos
            <span v-if="notificaciones.noLeidos.value > 0" class="inicio__badge">
              {{ notificaciones.noLeidos.value }}
              <span class="visualmente-oculto">sin leer</span>
            </span>
          </h2>
          <p v-if="avisos.length === 0" class="texto-secundario">No tienes avisos nuevos.</p>
          <TarjetaAviso
            v-for="a in avisos"
            :key="a.id"
            :aviso="a"
            @escuchar="a.song && player.play(a.song)"
            @aceptar="a.invite && notificaciones.aceptar(a.invite.token)"
            @ignorar="a.invite && notificaciones.ignorar(a.invite.token)"
          />
        </section>
      </div>
    </div>

    <section class="inicio__recientes" aria-labelledby="titulo-recientes">
      <header class="inicio__recientes-cabecera">
        <h2 id="titulo-recientes">Vuelve a lo que te gusta</h2>
        <RouterLink v-if="recientes.length" to="/historial" class="boton-texto">
          Ver todo <Icono nombre="arrow-right" :tam="14" />
        </RouterLink>
      </header>
      <div v-if="cargandoRecientes" class="esqueleto-fila" aria-hidden="true"><span /><span /></div>
      <AvisoEnLinea v-else-if="errorRecientes" reintentar @reintentar="cargarRecientes">
        No pudimos cargar lo que escuchaste.
      </AvisoEnLinea>
      <p v-else-if="recientes.length === 0" class="texto-secundario">
        Aún no escuchas nada. Empieza en el <RouterLink to="/catalogo">Catálogo</RouterLink>.
      </p>
      <ul v-else class="inicio__rejilla">
        <li v-for="h in recientes" :key="h.song.id">
          <FilaCancion
            :cancion="h.song"
            :disponible="h.available"
            :sonando="player.current.value?.id === h.song.id"
            @reproducir="reproducir(h)"
          />
        </li>
      </ul>
    </section>
  </section>
</template>

<style scoped>
.inicio {
  display: grid;
  gap: var(--space-6);
  padding: var(--space-5);
}

.inicio__cabecera {
  display: grid;
  gap: var(--space-2);
}

.inicio__columnas {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-4);
}

.inicio__apiladas {
  display: grid;
  align-content: start;
  gap: var(--space-4);
}

.inicio__crear,
.inicio__avisos {
  display: grid;
  gap: var(--space-3);
  justify-items: start;
}

.inicio__avisos {
  justify-items: stretch;
}

.inicio__subtitulo {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 20px;
}

.inicio__badge {
  display: inline-grid;
  place-items: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: var(--radius-pill);
  background: var(--accent);
  color: var(--on-accent);
  font-family: var(--font-body);
  font-size: 11px;
  font-weight: 700;
}

.inicio__recientes {
  display: grid;
  gap: var(--space-3);
}

.inicio__recientes-cabecera {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-3);
}

.inicio__recientes-cabecera a {
  text-decoration: none;
}

.inicio__rejilla {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-2) var(--space-4);
  margin: 0;
  padding: 0;
  list-style: none;
}

@media (max-width: 1100px) {
  .inicio__columnas,
  .inicio__rejilla {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 700px) {
  .inicio {
    padding: var(--space-4);
  }

  .inicio__columnas,
  .inicio__rejilla {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
