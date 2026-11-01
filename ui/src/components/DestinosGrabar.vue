<script setup lang="ts">
import { computed, ref } from 'vue'
import type { PlaylistSummary } from '../api/types'
import { useCasetes } from '../composables/useCasetes'
import CampoCaseteNuevo from './CampoCaseteNuevo.vue'
import Icono from './icons/Icono.vue'

// Casetes donde puedes grabar, el último usado primero, y "Nuevo casete…" en línea.
const props = defineProps<{ songId: string }>()
const emit = defineEmits<{ terminado: [caseteId: string | null] }>()
const { casetes, ultimoDestino, grabar } = useCasetes()

const creando = ref(false)
const ocupado = ref(false)

const destinos = computed(() => {
  const escribibles = casetes.value.filter((c) => c.role === 'owner' || c.role === 'collaborator')
  const ultimo = escribibles.find((c) => c.id === ultimoDestino.value)
  return ultimo ? [ultimo, ...escribibles.filter((c) => c !== ultimo)] : escribibles
})

/** Emite el casete si quedó grabada, o null si falló (el aviso ya se mostró). */
async function grabarEn(id: string): Promise<void> {
  if (ocupado.value) return
  ocupado.value = true
  try {
    emit('terminado', (await grabar(id, props.songId)) ? id : null)
  } finally {
    ocupado.value = false
  }
}

function onCreado(nuevo: PlaylistSummary): void {
  void grabarEn(nuevo.id)
}
</script>

<template>
  <div class="destinos">
    <p class="antetitulo">Grabar en casete</p>
    <ul class="destinos__lista">
      <li v-for="c in destinos" :key="c.id">
        <button
          type="button"
          class="destinos__opcion"
          data-prueba="destino"
          :disabled="ocupado"
          @click="grabarEn(c.id)"
        >
          <Icono nombre="disc-3" :tam="16" />
          <span class="destinos__nombre">{{ c.name }}</span>
          <span v-if="c.id === ultimoDestino" class="destinos__ultimo">Último usado</span>
        </button>
      </li>
    </ul>
    <CampoCaseteNuevo v-if="creando" @creado="onCreado" @cancelar="creando = false" />
    <button
      v-else
      type="button"
      class="destinos__opcion"
      data-prueba="nuevo-casete"
      @click="creando = true"
    >
      <Icono nombre="plus" :tam="16" />
      <span>Nuevo casete…</span>
    </button>
  </div>
</template>

<style scoped>
.destinos {
  display: grid;
  gap: var(--space-2);
}

.destinos__lista {
  display: grid;
  margin: 0;
  padding: 0;
  list-style: none;
}

.destinos__opcion {
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
  .destinos__opcion:not(:disabled):hover {
    background: color-mix(in srgb, var(--surface) 45%, transparent);
  }
}

.destinos__nombre {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.destinos__ultimo {
  color: var(--ink-muted);
  font-size: 10px;
}
</style>
