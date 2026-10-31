<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { ApiError } from '../api/http'
import * as metrics from '../api/metrics'
import type { TopSongOut } from '../api/types'
import AvisoEnLinea from './AvisoEnLinea.vue'
import BotonGrabar from './BotonGrabar.vue'

const LIMITE = 10
const REFRESCO_MS = 15_000

const top = ref<TopSongOut[]>([])
const cargando = ref(true)
const error = ref('')

let intervalo: ReturnType<typeof setInterval> | undefined
let enCurso = false

/** "1 284" con espacio fino como separador de miles (DESIGN.md §9). */
function conMiles(n: number): string {
  return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
}

function reproducciones(n: number): string {
  return `${conMiles(n)} ${n === 1 ? 'reproducción' : 'reproducciones'}`
}

async function actualizar(): Promise<void> {
  if (enCurso) return
  enCurso = true
  try {
    top.value = await metrics.top(LIMITE)
    error.value = ''
  } catch (e) {
    // El fallo se queda en este panel: el reproductor y los demás paneles siguen igual.
    error.value = e instanceof ApiError ? e.message : 'No pudimos cargar lo más escuchado.'
  } finally {
    enCurso = false
    cargando.value = false
  }
}

function reintentar(): void {
  cargando.value = top.value.length === 0
  void actualizar()
}

onMounted(() => {
  void actualizar()
  // Solo refresca mientras el panel está montado (pestaña activa) y la página se ve.
  intervalo = setInterval(() => {
    if (document.visibilityState === 'visible') void actualizar()
  }, REFRESCO_MS)
})

onBeforeUnmount(() => clearInterval(intervalo))
</script>

<template>
  <section class="top" aria-labelledby="titulo-top">
    <div class="top__encabezado">
      <h2 id="titulo-top">Lo más escuchado</h2>
      <p class="top__nota">Se actualiza cada pocos segundos</p>
    </div>

    <ol v-if="cargando" class="top__lista" aria-label="Cargando lo más escuchado…">
      <li v-for="n in 3" :key="n" class="top__esqueleto" aria-hidden="true"><span /><span /></li>
    </ol>

    <template v-else>
      <AvisoEnLinea v-if="error" reintentar @reintentar="reintentar">{{ error }}</AvisoEnLinea>

      <p v-if="!error && top.length === 0" class="top__vacio">
        Nadie ha escuchado nada todavía. Pon play y estrena el ranking.
      </p>

      <ol v-if="top.length > 0" class="top__lista">
        <li v-for="(cancion, i) in top" :key="cancion.song_id" class="top__fila">
          <span class="top__numero">{{ i + 1 }}</span>
          <span class="top__textos">
            <span class="top__titulo" :title="cancion.title">{{ cancion.title }}</span>
            <span class="top__detalle" :title="cancion.artist">{{ cancion.artist }}</span>
          </span>
          <span class="top__conteo">{{ reproducciones(cancion.play_count) }}</span>
          <BotonGrabar :song-id="cancion.song_id" :titulo="cancion.title" />
        </li>
      </ol>
    </template>
  </section>
</template>

<style scoped>
.top {
  display: grid;
  gap: var(--space-4);
  align-content: start;
}

.top__encabezado {
  display: grid;
  gap: var(--space-1);
}

.top__nota,
.top__vacio {
  margin: 0;
}

.top__nota,
.top__detalle,
.top__conteo {
  font-size: 13px;
  opacity: 0.8;
}

.top__lista {
  margin: 0;
  padding: 0;
  list-style: none;
}

.top__fila {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr) auto 40px;
  align-items: center;
  gap: var(--space-3);
  min-height: 56px;
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--rule);
}

.top__numero {
  font-family: var(--font-display);
  font-size: 22px;
  font-variation-settings: 'SOFT' 100;
  font-weight: 800;
  text-align: right;
}

.top__textos {
  display: grid;
  min-width: 0;
}

.top__titulo,
.top__detalle {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.top__titulo {
  font-weight: 700;
}

.top__conteo {
  font-variant-numeric: tabular-nums;
}

.top__esqueleto {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--rule);
}

.top__esqueleto span {
  width: 50%;
  height: 12px;
  border-radius: var(--radius-s);
  background: var(--rule);
}

.top__esqueleto span:last-child {
  width: 30%;
}

@media (max-width: 479px) {
  /* En pantallas muy angostas el conteo baja bajo el título para no forzar scroll horizontal. */
  .top__fila {
    grid-template-columns: 32px minmax(0, 1fr) 40px;
  }

  .top__conteo {
    grid-column: 2;
    grid-row: 2;
  }

  .top__fila :deep(.boton-grabar) {
    grid-column: 3;
    grid-row: 1 / span 2;
  }
}
</style>
