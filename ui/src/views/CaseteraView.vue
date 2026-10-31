<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import CaseteActivo from '../components/CaseteActivo.vue'
import ControlesReproductor from '../components/ControlesReproductor.vue'
import EstanteCasetes from '../components/EstanteCasetes.vue'
import InterruptorLado from '../components/InterruptorLado.vue'
import ListaCasete from '../components/ListaCasete.vue'
import PanelCatalogo from '../components/PanelCatalogo.vue'
import PanelTop from '../components/PanelTop.vue'
import { useCasetes } from '../composables/useCasetes'
import { usePlayer } from '../composables/usePlayer'
import { useSession } from '../composables/useSession'

type Pestana = 'catalogo' | 'casete' | 'top'

const ANCHO_ESCRITORIO = '(min-width: 900px)'

const { user, isAdmin, logout } = useSession()
const { activo, cargando, cargar } = useCasetes()
const player = usePlayer()

// En escritorio la lista del casete vive en la columna izquierda; en < 900 px pasa a una pestaña.
const consulta = typeof matchMedia === 'function' ? matchMedia(ANCHO_ESCRITORIO) : null
const ancho = ref(consulta?.matches ?? true)
function onCambioAncho(evento: MediaQueryListEvent): void {
  ancho.value = evento.matches
}

const pestanas = computed<ReadonlyArray<{ id: Pestana; texto: string }>>(() =>
  ancho.value
    ? [
        { id: 'catalogo', texto: 'Catálogo' },
        { id: 'top', texto: 'Lo más escuchado' },
      ]
    : [
        { id: 'catalogo', texto: 'Catálogo' },
        { id: 'casete', texto: 'Mi casete' },
        { id: 'top', texto: 'Lo más escuchado' },
      ],
)
const pestana = ref<Pestana>('catalogo')

// Al pasar a escritorio la pestaña "Mi casete" desaparece: se vuelve al catálogo.
watch(ancho, (esAncho) => {
  if (esAncho && pestana.value === 'casete') pestana.value = 'catalogo'
})

const etiqueta = computed(() => {
  if (activo.value) return activo.value.name
  return cargando.value ? 'Cargando casete…' : 'Elige un casete del estante'
})

function moverPestana(evento: KeyboardEvent): void {
  const lista = pestanas.value
  const actual = lista.findIndex((p) => p.id === pestana.value)
  let destino = actual
  if (evento.key === 'ArrowRight') destino = (actual + 1) % lista.length
  else if (evento.key === 'ArrowLeft') destino = (actual - 1 + lista.length) % lista.length
  else if (evento.key === 'Home') destino = 0
  else if (evento.key === 'End') destino = lista.length - 1
  else return
  evento.preventDefault()
  pestana.value = lista[destino].id
  void nextTick(() => document.getElementById(`pestana-${lista[destino].id}`)?.focus())
}

onMounted(() => {
  consulta?.addEventListener('change', onCambioAncho)
  void cargar()
})

onBeforeUnmount(() => {
  consulta?.removeEventListener('change', onCambioAncho)
})
</script>

<template>
  <div class="casetera" :class="{ 'casetera--ancho': ancho }">
    <h1 class="visualmente-oculto">Casetera</h1>

    <section class="casetera__deck" aria-label="Casetera">
      <div v-if="!ancho" class="casetera__compacta">
        <CaseteActivo class="casetera__casete-compacto" :etiqueta="etiqueta" :girando="player.isPlaying.value" compacto />
        <InterruptorLado />
      </div>
      <CaseteActivo v-else :etiqueta="etiqueta" :girando="player.isPlaying.value" />

      <ControlesReproductor />

      <template v-if="ancho">
        <ListaCasete class="casetera__lista" />
        <EstanteCasetes />
      </template>
    </section>

    <section class="casetera__tienda" aria-label="Tienda">
      <header class="tienda__encabezado">
        <p class="tienda__usuario" :title="user?.name">{{ user?.name }}</p>
        <nav class="tienda__acciones" aria-label="Cuenta">
          <RouterLink v-if="isAdmin" to="/cabina" class="tienda__enlace">Cabina de grabación</RouterLink>
          <button type="button" class="boton-contorno" @click="logout">Salir</button>
          <InterruptorLado v-if="ancho" />
        </nav>
      </header>

      <div class="tienda__pestanas" role="tablist" aria-label="Secciones" @keydown="moverPestana">
        <button
          v-for="p in pestanas"
          :id="`pestana-${p.id}`"
          :key="p.id"
          type="button"
          role="tab"
          class="tienda__pestana"
          :aria-selected="pestana === p.id"
          aria-controls="panel-tienda"
          :tabindex="pestana === p.id ? 0 : -1"
          @click="pestana = p.id"
        >
          {{ p.texto }}
        </button>
      </div>

      <div
        id="panel-tienda"
        class="tienda__panel"
        :class="{ 'tienda__panel--deck': pestana === 'casete' }"
        role="tabpanel"
        :aria-labelledby="`pestana-${pestana}`"
      >
        <PanelCatalogo v-if="pestana === 'catalogo'" />
        <div v-else-if="pestana === 'casete'" class="tienda__casete">
          <ListaCasete />
          <EstanteCasetes />
        </div>
        <PanelTop v-else />
      </div>
    </section>
  </div>
</template>

<style scoped>
.casetera {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* < 900 px: casetera compacta fija arriba; la tienda hace scroll con la página. */
.casetera__deck {
  position: sticky;
  top: 0;
  z-index: 2;
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--deck);
  color: var(--deck-ink);
}

.casetera__compacta {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.casetera__casete-compacto {
  flex: 1;
  min-width: 0;
}

.casetera__tienda {
  display: grid;
  gap: var(--space-4);
  align-content: start;
  min-width: 0;
  padding: var(--space-4);
}

.tienda__encabezado {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2) var(--space-3);
}

.tienda__usuario {
  min-width: 0;
  margin: 0;
  overflow: hidden;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tienda__acciones {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2) var(--space-3);
}

.tienda__enlace {
  display: inline-flex;
  align-items: center;
  min-height: 40px;
  color: var(--ink);
  font-weight: 500;
  text-underline-offset: 3px;
}

.boton-contorno {
  min-height: 40px;
  padding: 0 var(--space-4);
  border: 2px solid currentColor;
  border-radius: 999px;
  background: transparent;
  font-weight: 500;
}

@media (hover: hover) {
  .boton-contorno:hover,
  .tienda__pestana[aria-selected='false']:hover {
    background: color-mix(in srgb, currentColor 12%, transparent);
  }
}

.tienda__pestanas {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.tienda__pestana {
  flex: none;
  min-height: 40px;
  padding: 0 var(--space-4);
  border: 2px solid var(--ink);
  border-radius: 999px;
  background: transparent;
  font-weight: 500;
}

.tienda__pestana[aria-selected='true'] {
  background: var(--ink);
  color: var(--bg);
  font-weight: 700;
}

.tienda__panel {
  min-width: 0;
}

/* "Mi casete" en < 900 px conserva el fondo de la casetera para respetar los contrastes. */
.tienda__panel--deck {
  margin: 0 calc(-1 * var(--space-4));
  padding: var(--space-4);
  background: var(--deck);
}

.tienda__casete {
  display: grid;
  gap: var(--space-5);
}

/* ≥ 900 px: dos columnas a todo el alto; cada lista hace scroll por dentro. */
.casetera--ancho {
  display: grid;
  grid-template-columns: minmax(360px, 1fr) 1.15fr;
  height: 100vh;
  height: 100dvh;
}

.casetera--ancho .casetera__deck {
  position: static;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  min-height: 0;
  padding: var(--space-5);
}

.casetera--ancho .casetera__lista {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.casetera--ancho .casetera__tienda {
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: var(--space-5);
}

.casetera--ancho .tienda__panel {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  /* Deja ver el anillo de foco de las filas dentro del scroll. */
  padding: var(--space-1);
}
</style>
