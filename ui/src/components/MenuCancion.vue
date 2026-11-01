<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import type { SongOut } from '../api/types'
import { useCasetes } from '../composables/useCasetes'
import { useFavoritos } from '../composables/useFavoritos'
import { usePlayer } from '../composables/usePlayer'
import DestinosGrabar from './DestinosGrabar.vue'
import Icono from './icons/Icono.vue'

// Menú "…" de una canción (DESIGN.md §7.5). Sin disponibilidad solo queda quitar de favoritas.
const props = withDefaults(defineProps<{ cancion: SongOut; disponible?: boolean }>(), {
  disponible: true,
})
const favoritos = useFavoritos()
const player = usePlayer()
const { casetes, cargar } = useCasetes()

const abierto = ref(false)
const grabando = ref(false)
const raiz = ref<HTMLElement | null>(null)
const disparador = ref<HTMLButtonElement | null>(null)

function opciones(): HTMLElement[] {
  return Array.from(raiz.value?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? [])
}

async function alternar(): Promise<void> {
  abierto.value = !abierto.value
  grabando.value = false
  if (!abierto.value) return
  await nextTick()
  opciones()[0]?.focus()
}

function cerrar(devolverFoco = true): void {
  abierto.value = false
  grabando.value = false
  if (devolverFoco) disparador.value?.focus()
}

async function abrirGrabar(): Promise<void> {
  if (casetes.value.length === 0) await cargar()
  grabando.value = true
  await nextTick()
  raiz.value?.querySelector<HTMLElement>('[data-prueba="destino"], [data-prueba="nuevo-casete"]')?.focus()
}

function ejecutar(accion: () => unknown): void {
  void accion()
  cerrar()
}

function onTeclaMenu(evento: KeyboardEvent): void {
  if (grabando.value) return
  const lista = opciones()
  const actual = lista.indexOf(document.activeElement as HTMLElement)
  let destino = -1
  if (evento.key === 'ArrowDown') destino = (actual + 1) % lista.length
  else if (evento.key === 'ArrowUp') destino = (actual - 1 + lista.length) % lista.length
  else if (evento.key === 'Home') destino = 0
  else if (evento.key === 'End') destino = lista.length - 1
  if (destino < 0) return
  evento.preventDefault()
  lista[destino]?.focus()
}

function onDocumento(evento: Event): void {
  if (!abierto.value) return
  if (evento instanceof KeyboardEvent) {
    if (evento.key === 'Escape') cerrar()
  } else if (raiz.value && !raiz.value.contains(evento.target as Node)) {
    cerrar(false)
  }
}
onMounted(() => {
  document.addEventListener('keydown', onDocumento)
  document.addEventListener('pointerdown', onDocumento)
})
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onDocumento)
  document.removeEventListener('pointerdown', onDocumento)
})
</script>

<template>
  <div ref="raiz" class="menu-cancion">
    <button
      ref="disparador"
      type="button"
      class="boton-icono"
      :aria-label="`Más opciones para «${cancion.title}»`"
      aria-haspopup="menu"
      :aria-expanded="abierto"
      @click="alternar"
    >
      <Icono nombre="ellipsis" :tam="18" />
    </button>

    <div v-if="abierto && grabando" class="popover menu-cancion__popover" role="dialog" :aria-label="`Grabar «${cancion.title}»`">
      <DestinosGrabar :song-id="cancion.id" @terminado="cerrar()" />
    </div>
    <ul
      v-else-if="abierto"
      class="popover menu-cancion__popover menu-cancion__lista"
      role="menu"
      :aria-label="`Opciones de «${cancion.title}»`"
      @keydown="onTeclaMenu"
    >
      <li v-if="disponible" role="none">
        <button type="button" role="menuitem" class="menu-cancion__opcion" @click="abrirGrabar">
          <Icono nombre="disc-3" :tam="16" /> Grabar en casete…
        </button>
      </li>
      <li role="none">
        <button
          type="button"
          role="menuitem"
          class="menu-cancion__opcion"
          @click="ejecutar(() => favoritos.alternar(props.cancion.id))"
        >
          <Icono nombre="heart" :tam="16" />
          {{ favoritos.esFavorita(cancion.id) ? 'Quitar de favoritas' : 'Añadir a favoritas' }}
        </button>
      </li>
      <li v-if="disponible" role="none">
        <button type="button" role="menuitem" class="menu-cancion__opcion" @click="ejecutar(() => player.enqueue(props.cancion))">
          <Icono nombre="list-music" :tam="16" /> Añadir a la cola
        </button>
      </li>
      <li v-if="disponible" role="none">
        <button type="button" role="menuitem" class="menu-cancion__opcion" @click="ejecutar(() => player.playNext(props.cancion))">
          <Icono nombre="arrow-up-right" :tam="16" /> Reproducir a continuación
        </button>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.menu-cancion {
  position: relative;
  display: inline-flex;
}

.menu-cancion__popover {
  top: calc(100% + var(--space-1));
  right: 0;
}

.menu-cancion__lista {
  margin: 0;
  list-style: none;
  gap: 0;
}

.menu-cancion__opcion {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  min-height: 36px;
  padding: 0 var(--space-2);
  border: 0;
  border-radius: var(--radius-m);
  background: transparent;
  color: var(--ink);
  text-align: left;
  white-space: nowrap;
}

@media (hover: hover) {
  .menu-cancion__opcion:hover {
    background: color-mix(in srgb, var(--surface) 45%, transparent);
  }
}
</style>
