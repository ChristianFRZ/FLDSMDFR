<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import type { PlaylistSummary } from '../api/types'
import { useCasetes } from '../composables/useCasetes'
import CampoCaseteNuevo from './CampoCaseteNuevo.vue'
import Icono from './icons/Icono.vue'

// Popover "Grabar en casete": casetes donde puedes grabar, el último usado primero (DESIGN.md §7.7).
const props = defineProps<{ songId: string; titulo: string }>()
const emit = defineEmits<{ grabado: [caseteId: string] }>()
const { casetes, ultimoDestino, cargar, grabar } = useCasetes()

const abierto = ref(false)
const creando = ref(false)
const ocupado = ref(false)
const raiz = ref<HTMLElement | null>(null)
const disparador = ref<HTMLButtonElement | null>(null)

const destinos = computed(() => {
  const escribibles = casetes.value.filter((c) => c.role === 'owner' || c.role === 'collaborator')
  const ultimo = escribibles.find((c) => c.id === ultimoDestino.value)
  return ultimo ? [ultimo, ...escribibles.filter((c) => c !== ultimo)] : escribibles
})

async function abrir(): Promise<void> {
  abierto.value = !abierto.value
  creando.value = false
  if (abierto.value && casetes.value.length === 0) await cargar()
  if (abierto.value) {
    await nextTick()
    raiz.value?.querySelector<HTMLElement>('[data-prueba="destino"], [data-prueba="nuevo-casete"]')?.focus()
  }
}

function cerrar(devolverFoco = true): void {
  abierto.value = false
  creando.value = false
  if (devolverFoco) disparador.value?.focus()
}

async function grabarEn(id: string): Promise<void> {
  if (ocupado.value) return
  ocupado.value = true
  try {
    const ok = await grabar(id, props.songId)
    cerrar()
    if (ok) emit('grabado', id)
  } finally {
    ocupado.value = false
  }
}

function onCreado(nuevo: PlaylistSummary): void {
  void grabarEn(nuevo.id)
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
  <div ref="raiz" class="selector">
    <button
      ref="disparador"
      type="button"
      class="boton-icono"
      :aria-label="`Grabar «${titulo}» en un casete`"
      aria-haspopup="dialog"
      :aria-expanded="abierto"
      @click="abrir"
    >
      <Icono nombre="plus" :tam="18" />
    </button>

    <div v-if="abierto" class="selector__popover" role="dialog" :aria-label="`Grabar «${titulo}»`">
      <p class="antetitulo">Grabar en casete</p>
      <ul class="selector__lista">
        <li v-for="c in destinos" :key="c.id">
          <button
            type="button"
            class="selector__opcion"
            data-prueba="destino"
            :disabled="ocupado"
            @click="grabarEn(c.id)"
          >
            <Icono nombre="disc-3" :tam="16" />
            <span class="selector__nombre">{{ c.name }}</span>
            <span v-if="c.id === ultimoDestino" class="selector__ultimo">Último usado</span>
          </button>
        </li>
      </ul>
      <CampoCaseteNuevo v-if="creando" @creado="onCreado" @cancelar="creando = false" />
      <button
        v-else
        type="button"
        class="selector__opcion"
        data-prueba="nuevo-casete"
        @click="creando = true"
      >
        <Icono nombre="plus" :tam="16" />
        <span>Nuevo casete…</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.selector {
  position: relative;
  display: inline-flex;
}

.selector__popover {
  position: absolute;
  top: calc(100% + var(--space-1));
  right: 0;
  z-index: 40;
  display: grid;
  gap: var(--space-2);
  width: 240px;
  max-height: 320px;
  padding: var(--space-3);
  overflow-y: auto;
  border: 1px solid var(--surface);
  border-radius: var(--radius-l);
  background: var(--bg);
  box-shadow: 0 12px 32px rgb(0 0 0 / 35%);
}

.selector__lista {
  display: grid;
  margin: 0;
  padding: 0;
  list-style: none;
}

.selector__opcion {
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
}

@media (hover: hover) {
  .selector__opcion:not(:disabled):hover {
    background: color-mix(in srgb, var(--surface) 45%, transparent);
  }
}

.selector__nombre {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.selector__ultimo {
  color: var(--ink-muted);
  font-size: 10px;
}
</style>
