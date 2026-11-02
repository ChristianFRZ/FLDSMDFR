<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ApiError } from '../api/http'
import type { PlaylistSummary } from '../api/types'
import { useCasetes } from '../composables/useCasetes'

// Campo en línea para crear un casete: Enter crea, Esc cancela. Lo usan la biblioteca y el selector.
const emit = defineEmits<{ creado: [casete: PlaylistSummary]; cancelar: [] }>()
const { crear } = useCasetes()

const MAX_NOMBRE = 80
const nombre = ref('')
const error = ref('')
const enviando = ref(false)
const campo = ref<HTMLInputElement | null>(null)
onMounted(() => campo.value?.focus())

async function confirmar(): Promise<void> {
  const limpio = nombre.value.trim()
  if (enviando.value) return
  if (!limpio) {
    error.value = 'Escribe un nombre para el casete.'
    return
  }
  enviando.value = true
  error.value = ''
  try {
    emit('creado', await crear(limpio))
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'No pudimos crear el casete. Vuelve a intentarlo.'
  } finally {
    enviando.value = false
  }
}

function onKeydown(evento: KeyboardEvent): void {
  if (evento.key === 'Enter') {
    evento.preventDefault()
    void confirmar()
  } else if (evento.key === 'Escape') {
    evento.preventDefault()
    evento.stopPropagation()
    emit('cancelar')
  }
}
</script>

<template>
  <div class="campo-nuevo">
    <input
      ref="campo"
      v-model="nombre"
      class="campo-nuevo__input"
      type="text"
      :maxlength="MAX_NOMBRE"
      placeholder="Nombre del casete"
      aria-label="Nombre del casete nuevo"
      :aria-invalid="!!error"
      :aria-describedby="error ? 'error-casete-nuevo' : undefined"
      :disabled="enviando"
      @keydown="onKeydown"
    />
    <p v-if="error" id="error-casete-nuevo" class="campo__error" role="alert">{{ error }}</p>
  </div>
</template>

<style scoped>
.campo-nuevo {
  display: grid;
  gap: var(--space-1);
}

.campo-nuevo__input {
  width: 100%;
  min-height: 36px;
  padding: 0 var(--space-3);
  border: 1px solid var(--surface);
  border-radius: var(--radius-m);
  background: var(--bg);
  color: var(--ink);
}
</style>
