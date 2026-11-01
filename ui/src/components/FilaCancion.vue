<script setup lang="ts">
import { computed } from 'vue'
import * as songs from '../api/songs'
import type { SongOut } from '../api/types'
import { formatTime } from '../composables/formatTime'
import MenuCancion from './MenuCancion.vue'
import Portada from './Portada.vue'
import Icono from './icons/Icono.vue'

// Fila de canción: portada, título, artista, duración y menú "…" (DESIGN.md §7.5).
const props = withDefaults(
  defineProps<{ cancion: SongOut; sonando?: boolean; disponible?: boolean; tamPortada?: number }>(),
  { sonando: false, disponible: true, tamPortada: 44 },
)
const emit = defineEmits<{ reproducir: [] }>()

const portada = computed(() => (props.cancion.has_cover ? songs.coverUrl(props.cancion.id) : null))

function reproducir(): void {
  if (props.disponible) emit('reproducir')
}
</script>

<template>
  <div class="fila" :class="{ 'fila--sonando': sonando, 'fila--no-disponible': !disponible }">
    <button
      type="button"
      class="fila__principal"
      data-prueba="reproducir"
      :aria-label="disponible ? `Reproducir «${cancion.title}» de ${cancion.artist}` : `«${cancion.title}» no está disponible`"
      :aria-current="sonando ? 'true' : undefined"
      :disabled="!disponible"
      @click="reproducir"
    >
      <Portada :src="portada" :titulo="cancion.title" :tam="tamPortada" />
      <span class="fila__texto">
        <span class="fila__titulo">{{ cancion.title }}</span>
        <span class="fila__artista">{{ disponible ? cancion.artist : 'No disponible' }}</span>
      </span>
      <Icono v-if="sonando" nombre="audio-lines" :tam="16" class="fila__sonando" />
      <span class="fila__duracion">{{ formatTime(cancion.duration_seconds) }}</span>
    </button>
    <slot name="acciones" />
    <MenuCancion :cancion="cancion" :disponible="disponible" />
  </div>
</template>

<style scoped>
.fila {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1);
  border-radius: var(--radius-m);
}

@media (hover: hover) {
  .fila:not(.fila--sonando):hover {
    background: color-mix(in srgb, var(--surface) 45%, transparent);
  }
}

.fila--sonando {
  background: var(--surface-active);
  color: var(--ink-on-active);
}

.fila__principal {
  display: flex;
  flex: 1;
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
  padding: 0;
  border: 0;
  border-radius: var(--radius-s);
  background: transparent;
  color: inherit;
  text-align: left;
}

.fila__texto {
  display: grid;
  flex: 1;
  min-width: 0;
}

.fila__titulo,
.fila__artista {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fila__titulo {
  font-weight: 600;
}

.fila__artista {
  color: var(--ink-muted);
  font-size: 11px;
}

.fila--sonando .fila__artista {
  color: var(--ink-on-active);
}

.fila__duracion {
  min-width: 36px;
  color: var(--ink-muted);
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  text-align: right;
}

.fila--sonando .fila__duracion {
  color: var(--ink-on-active);
}
</style>
