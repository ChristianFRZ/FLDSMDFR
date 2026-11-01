<script setup lang="ts">
import { ref } from 'vue'
import * as playlists from '../api/playlists'
import { useAvisos } from '../composables/useAvisos'
import Icono from './icons/Icono.vue'

// Enlace de invitación del casete (solo el dueño): generar, copiar y revocar.
const props = defineProps<{ caseteId: string }>()
const emit = defineEmits<{ fallo: [error: unknown] }>()
const { mostrar } = useAvisos()

const enlace = ref('')
const ocupado = ref(false)
const campo = ref<HTMLInputElement | null>(null)

async function generar(): Promise<void> {
  ocupado.value = true
  try {
    const invitacion = await playlists.createInvite(props.caseteId)
    enlace.value = new URL(invitacion.url, location.origin).toString()
  } catch (e) {
    emit('fallo', e)
  } finally {
    ocupado.value = false
  }
}

async function copiar(): Promise<void> {
  try {
    await navigator.clipboard.writeText(enlace.value)
    mostrar('Enlace copiado.', 'info')
  } catch {
    campo.value?.select()
    mostrar('No pudimos copiarlo: selecciona el enlace y cópialo a mano.', 'error')
  }
}

async function revocar(): Promise<void> {
  ocupado.value = true
  try {
    await playlists.revokeInvite(props.caseteId)
    enlace.value = ''
    mostrar('El enlace anterior ya no sirve.', 'info')
  } catch (e) {
    emit('fallo', e)
  } finally {
    ocupado.value = false
  }
}
</script>

<template>
  <section class="compartir tarjeta" aria-labelledby="titulo-compartir">
    <h2 id="titulo-compartir" class="compartir__titulo">Compartir</h2>
    <p class="texto-secundario">
      Quien abra el enlace podrá unirse y grabar canciones. Generar uno nuevo anula el anterior.
    </p>
    <div v-if="enlace" class="compartir__enlace">
      <input
        ref="campo"
        class="compartir__campo"
        type="text"
        readonly
        aria-label="Enlace de invitación"
        :value="enlace"
        @focus="campo?.select()"
      />
      <button type="button" class="boton-principal" data-prueba="copiar-enlace" @click="copiar">
        <Icono nombre="copy" :tam="14" /> Copiar enlace
      </button>
    </div>
    <div class="compartir__acciones">
      <button
        type="button"
        class="boton-contorno"
        data-prueba="generar-enlace"
        :disabled="ocupado"
        @click="generar"
      >
        <Icono nombre="link" :tam="14" /> {{ enlace ? 'Generar otro enlace' : 'Generar enlace' }}
      </button>
      <button
        type="button"
        class="boton-texto boton-texto--secundario"
        :disabled="ocupado"
        @click="revocar"
      >
        Revocar enlace
      </button>
    </div>
  </section>
</template>

<style scoped>
.compartir {
  display: grid;
  gap: var(--space-3);
}

.compartir__titulo {
  font-size: 20px;
}

.compartir__enlace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space-2);
}

.compartir__campo {
  min-width: 0;
  min-height: 32px;
  padding: 0 var(--space-3);
  border: 1px solid var(--surface);
  border-radius: var(--radius-m);
  background: var(--bg);
  color: var(--ink);
}

.compartir__acciones {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
</style>
