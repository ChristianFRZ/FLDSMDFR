<script setup lang="ts">
// Totales y top 10 de la cabina (GET /api/metrics/summary).
import { onMounted, ref } from 'vue'
import { ApiError } from '../api/http'
import * as metrics from '../api/metrics'
import type { MetricsSummary } from '../api/types'
import AvisoEnLinea from './AvisoEnLinea.vue'

const TOP_MAXIMO = 10

const resumen = ref<MetricsSummary | null>(null)
const cargando = ref(true)
const error = ref('')

async function cargar(): Promise<void> {
  cargando.value = resumen.value === null
  error.value = ''
  try {
    resumen.value = await metrics.summary()
  } catch (e) {
    error.value =
      e instanceof ApiError ? e.message : 'No pudimos cargar el resumen. Vuelve a intentarlo.'
  } finally {
    cargando.value = false
  }
}

onMounted(() => void cargar())
defineExpose({ recargar: cargar })
</script>

<template>
  <section class="resumen" aria-labelledby="titulo-resumen">
    <h2 id="titulo-resumen">Resumen</h2>

    <div v-if="cargando" class="resumen__tarjetas" aria-label="Cargando resumen…">
      <div v-for="n in 3" :key="n" class="resumen__tarjeta resumen__tarjeta--esqueleto" aria-hidden="true" />
    </div>

    <AvisoEnLinea v-else-if="error && !resumen" reintentar @reintentar="cargar">{{ error }}</AvisoEnLinea>

    <template v-else-if="resumen">
      <AvisoEnLinea v-if="error" reintentar @reintentar="cargar">{{ error }}</AvisoEnLinea>
      <dl class="resumen__tarjetas">
        <div class="resumen__tarjeta">
          <dt>reproducciones</dt>
          <dd>{{ resumen.total_playbacks.toLocaleString('es-MX') }}</dd>
        </div>
        <div class="resumen__tarjeta">
          <dt>canciones</dt>
          <dd>{{ resumen.total_songs.toLocaleString('es-MX') }}</dd>
        </div>
        <div class="resumen__tarjeta">
          <dt>usuarios</dt>
          <dd>{{ resumen.total_users.toLocaleString('es-MX') }}</dd>
        </div>
      </dl>

      <h3 id="titulo-top-cabina">Lo más escuchado</h3>
      <ol v-if="resumen.top.length" class="resumen__top" aria-labelledby="titulo-top-cabina">
        <li v-for="cancion in resumen.top.slice(0, TOP_MAXIMO)" :key="cancion.song_id">
          <span class="resumen__cancion" :title="`${cancion.title} · ${cancion.artist}`">
            {{ cancion.title }} · {{ cancion.artist }}
          </span>
          <span class="resumen__cuenta">{{ cancion.play_count }}</span>
        </li>
      </ol>
      <p v-else class="resumen__vacio">Nadie ha escuchado nada todavía.</p>
    </template>
  </section>
</template>

<style scoped>
.resumen {
  display: grid;
  gap: var(--space-3);
}

.resumen__tarjetas {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-2);
  margin: 0;
}

.resumen__tarjeta {
  display: flex;
  flex-direction: column-reverse; /* <dt> primero en el DOM, pero el número se ve arriba */
  gap: var(--space-1);
  min-width: 0;
  padding: var(--space-3);
  border-radius: var(--radius-m);
  background: var(--surface);
  color: var(--ink);
}

.resumen__tarjeta--esqueleto {
  min-height: 72px;
  opacity: 0.5;
}

.resumen__tarjeta dd {
  margin: 0;
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 800;
  line-height: 1.1;
  overflow-wrap: anywhere;
}

.resumen__tarjeta dt {
  font-size: 13px;
}

.resumen__top {
  display: grid;
  gap: var(--space-1);
  margin: 0;
  padding-left: var(--space-5);
}

.resumen__top li {
  padding-left: var(--space-1);
}

.resumen__cancion {
  display: inline-block;
  max-width: calc(100% - 4rem);
  overflow: hidden;
  text-overflow: ellipsis;
  vertical-align: bottom;
  white-space: nowrap;
}

.resumen__cuenta {
  float: right;
  font-variant-numeric: tabular-nums;
}

.resumen__vacio {
  margin: 0;
}
</style>
