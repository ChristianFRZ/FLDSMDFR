<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import * as me from '../api/me'
import type { HistoryItemOut } from '../api/types'
import AvisoEnLinea from '../components/AvisoEnLinea.vue'
import FilaCancion from '../components/FilaCancion.vue'
import { tiempoRelativo } from '../composables/texto'
import { usePlayer } from '../composables/usePlayer'

// Todo lo escuchado, del más reciente al más antiguo, de 20 en 20.
const PAGINA = 20
const player = usePlayer()

const items = ref<HistoryItemOut[]>([])
const cargando = ref(false)
const error = ref(false)
const iniciado = ref(false)
// Posición en el servidor: puede adelantarse a items.length si se descartaron repetidas.
let desde = 0

const hayMas = ref(false)
const disponibles = computed(() => items.value.filter((h) => h.available).map((h) => h.song))

async function cargar(): Promise<void> {
  cargando.value = true
  error.value = false
  try {
    const pagina = await me.history(PAGINA, desde)
    // Una canción escuchada entre páginas puede repetirse: se conserva la primera aparición.
    const vistos = new Set(items.value.map((h) => h.song.id))
    items.value = [...items.value, ...pagina.items.filter((h) => !vistos.has(h.song.id))]
    desde += pagina.items.length
    hayMas.value = pagina.items.length > 0 && desde < pagina.total
  } catch {
    error.value = true
  } finally {
    cargando.value = false
    iniciado.value = true
  }
}
onMounted(cargar)

function reproducir(item: HistoryItemOut): void {
  if (item.available) void player.play(item.song, disponibles.value)
}
</script>

<template>
  <section class="historial" aria-labelledby="titulo-historial">
    <header>
      <p class="antetitulo">LO QUE ESCUCHASTE</p>
      <h1 id="titulo-historial">Historial</h1>
    </header>

    <div v-if="!iniciado" class="esqueleto-fila" aria-hidden="true"><span /><span /></div>
    <p v-else-if="items.length === 0 && !error" class="texto-secundario">
      Aún no escuchas nada. Empieza en el <RouterLink to="/catalogo">Catálogo</RouterLink>.
    </p>
    <ul v-if="items.length" class="historial__lista">
      <li v-for="h in items" :key="h.song.id" class="historial__item">
        <FilaCancion
          :cancion="h.song"
          :disponible="h.available"
          :sonando="player.current.value?.id === h.song.id"
          @reproducir="reproducir(h)"
        />
        <span class="historial__cuando">{{ tiempoRelativo(h.last_played_at) }}</span>
      </li>
    </ul>
    <AvisoEnLinea v-if="error" reintentar @reintentar="cargar">
      No pudimos cargar tu historial.
    </AvisoEnLinea>
    <button
      v-if="hayMas && !error"
      type="button"
      class="boton-contorno historial__mas"
      :disabled="cargando"
      :aria-busy="cargando"
      @click="cargar"
    >
      {{ cargando ? 'Cargando…' : 'Cargar más' }}
    </button>
  </section>
</template>

<style scoped>
.historial {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-5);
}

.historial__lista {
  display: grid;
  gap: var(--space-1);
  margin: 0;
  padding: 0;
  list-style: none;
}

.historial__item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 96px;
  align-items: center;
  gap: var(--space-3);
}

.historial__cuando {
  color: var(--ink-muted);
  font-size: 11px;
  text-align: right;
}

.historial__mas {
  justify-self: center;
}

@media (max-width: 700px) {
  .historial {
    padding: var(--space-4);
  }

  .historial__item {
    grid-template-columns: minmax(0, 1fr);
  }

  .historial__cuando {
    display: none;
  }
}
</style>
