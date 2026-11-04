<script setup lang="ts">
// Tarjeta "Resiliencia" de la Cabina (DESIGN.md §7): el circuit breaker de cada servicio que
// llama a otros, refrescado cada 2 s mientras la pestaña está visible (rama 04).
import { onBeforeUnmount, onMounted, ref } from 'vue'
import * as metrics from '../api/metrics'
import type { CircuitOut, CircuitsOut, CircuitState } from '../api/types'
import * as users from '../api/users'
import Icono from './icons/Icono.vue'

const REFRESCO_MS = 2000

interface Fuente {
  servicio: string
  pedir: () => Promise<CircuitsOut>
  datos: CircuitsOut | null
  error: boolean
}

const fuentes = ref<Fuente[]>([
  { servicio: 'users-playlists', pedir: users.circuits, datos: null, error: false },
  { servicio: 'playback-metrics', pedir: metrics.circuits, datos: null, error: false },
])

const NOMBRES: Record<CircuitState, string> = {
  closed: 'Cerrado',
  open: 'Abierto',
  half_open: 'Semiabierto',
}
// Indicador no cromático junto al texto: el estado no depende solo del color.
const ICONOS: Record<CircuitState, 'check' | 'x' | 'loader-circle'> = {
  closed: 'check',
  open: 'x',
  half_open: 'loader-circle',
}

function hace(since: string): string {
  const s = Math.max(0, Math.round((Date.now() - new Date(since).getTime()) / 1000))
  return `desde hace ${s} s`
}

function detalle(c: CircuitOut): string {
  const partes = [`${c.consecutive_failures} ${c.consecutive_failures === 1 ? 'falla' : 'fallas'} seguidas`, hace(c.since)]
  if (c.state === 'open' && c.retry_in_s !== null) partes.push(`vuelve a probar en ${Math.ceil(c.retry_in_s)} s`)
  return partes.join(' · ')
}

async function cargar(): Promise<void> {
  // Cada mitad por su lado: si un servicio no responde, la otra sigue mostrándose.
  await Promise.all(
    fuentes.value.map(async (f) => {
      try {
        f.datos = await f.pedir()
        f.error = false
      } catch {
        f.error = true
      }
    }),
  )
}

let temporizador: ReturnType<typeof setInterval> | undefined

function alCambiarVisibilidad(): void {
  if (!document.hidden) void cargar()
}

onMounted(() => {
  void cargar()
  temporizador = setInterval(() => {
    if (!document.hidden) void cargar()
  }, REFRESCO_MS)
  document.addEventListener('visibilitychange', alCambiarVisibilidad)
})

onBeforeUnmount(() => {
  clearInterval(temporizador)
  document.removeEventListener('visibilitychange', alCambiarVisibilidad)
})
</script>

<template>
  <section class="circuitos" aria-labelledby="titulo-circuitos">
    <h2 id="titulo-circuitos">Resiliencia</h2>
    <p class="circuitos__ayuda">
      Circuit breaker de cada llamada entre servicios: se abre tras 5 fallas seguidas y vuelve a
      probar a los 10 s.
    </p>

    <div v-for="f in fuentes" :key="f.servicio" class="circuitos__fuente">
      <h3>{{ f.servicio }}</h3>
      <p v-if="f.error" class="circuitos__sin-datos">Sin datos de {{ f.servicio }}</p>
      <template v-else-if="f.datos">
        <p class="circuitos__instancia">Instancia {{ f.datos.instance }}</p>
        <p v-if="f.datos.circuits.length === 0" class="circuitos__vacio">
          Todavía no hay llamadas a otros servicios.
        </p>
        <ul v-else class="circuitos__lista">
          <li
            v-for="c in f.datos.circuits"
            :key="c.target"
            class="circuitos__circuito"
            :class="`circuitos__circuito--${c.state}`"
          >
            <span class="circuitos__ruta">{{ c.source }} → {{ c.target }}</span>
            <span class="circuitos__estado">
              <Icono :nombre="ICONOS[c.state]" :tam="14" />
              {{ NOMBRES[c.state] }}
            </span>
            <span class="circuitos__detalle">{{ detalle(c) }}</span>
          </li>
        </ul>
      </template>
      <div v-else class="esqueleto-fila" aria-hidden="true"><span /><span /></div>
    </div>
  </section>
</template>

<style scoped>
.circuitos {
  display: grid;
  gap: var(--space-3);
}

.circuitos__ayuda,
.circuitos__instancia,
.circuitos__vacio,
.circuitos__sin-datos {
  margin: 0;
  color: var(--ink-muted);
  font-size: 11px;
}

.circuitos__sin-datos {
  color: var(--danger);
}

.circuitos__fuente {
  display: grid;
  gap: var(--space-2);
}

.circuitos__fuente h3 {
  margin: 0;
  font-size: 13px;
}

.circuitos__lista {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.circuitos__circuito {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space-1) var(--space-2);
  padding: var(--space-3);
  border-radius: var(--radius-m);
  background: var(--surface);
}

.circuitos__ruta {
  overflow: hidden;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.circuitos__estado {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-weight: 600;
}

.circuitos__circuito--open .circuitos__estado {
  color: var(--danger);
}

.circuitos__detalle {
  grid-column: 1 / -1;
  color: var(--ink-muted);
  font-size: 11px;
  font-variant-numeric: tabular-nums;
}
</style>
