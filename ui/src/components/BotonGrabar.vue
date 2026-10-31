<script setup lang="ts">
// Botón "+" que graba una canción en el casete activo (DESIGN.md §6.6). Lo usan Catálogo y Top.
import { computed, ref } from 'vue'
import { useCasetes } from '../composables/useCasetes'

const props = defineProps<{ songId: string; titulo: string }>()

const { activo, grabar } = useCasetes()
const grabando = ref(false)

const yaGrabada = computed(() => activo.value?.songs.some((s) => s.song_id === props.songId) ?? false)
const sinCasete = computed(() => !activo.value)

async function onClick(): Promise<void> {
  // Sin casete se deja pulsar: useCasetes explica "Crea un casete primero.".
  if (grabando.value || yaGrabada.value) return
  grabando.value = true
  try {
    await grabar(props.songId)
  } finally {
    grabando.value = false
  }
}
</script>

<template>
  <button
    v-if="yaGrabada"
    type="button"
    class="boton-grabar"
    aria-label="Ya está en el casete"
    title="Ya está en el casete"
    disabled
  >
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path d="M5 12.5l4.5 4.5L19 7.5" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
    </svg>
  </button>
  <button
    v-else
    type="button"
    class="boton-grabar"
    :class="{ 'boton-grabar--inactivo': sinCasete }"
    :aria-label="`Grabar «${titulo}» en el casete`"
    :aria-disabled="sinCasete || undefined"
    :aria-busy="grabando || undefined"
    :title="sinCasete ? 'Elige o crea un casete para grabar' : undefined"
    @click.stop="onClick"
  >
    <svg v-if="grabando" class="boton-grabar__carga" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path d="M12 4a8 8 0 1 1-8 8" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" />
    </svg>
    <svg v-else viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="3" stroke-linecap="round" />
    </svg>
  </button>
</template>

<style scoped>
.boton-grabar {
  display: inline-flex;
  flex: none;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: var(--accent);
  color: var(--on-accent);
}

.boton-grabar--inactivo {
  cursor: not-allowed;
  opacity: 0.45;
}

@media (hover: hover) {
  .boton-grabar:not(:disabled, .boton-grabar--inactivo):hover {
    filter: brightness(1.08);
  }
}

.boton-grabar:active:not(:disabled, .boton-grabar--inactivo) {
  transform: scale(0.96);
  transition: transform 80ms;
}

.boton-grabar__carga {
  animation: girar 0.9s linear infinite;
}

@keyframes girar {
  to {
    transform: rotate(360deg);
  }
}
</style>
