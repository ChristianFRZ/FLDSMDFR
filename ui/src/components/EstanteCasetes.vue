<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { ApiError } from '../api/http'
import { useCasetes } from '../composables/useCasetes'

type Modo = 'reposo' | 'crear' | 'renombrar' | 'borrar'

const MAX_NOMBRE = 60

const { casetes, activo, cargando, seleccionar, crear, renombrar, eliminar } = useCasetes()

const modo = ref<Modo>('reposo')
const nombre = ref('')
const errorCampo = ref('')
const enviando = ref(false)
const campo = ref<HTMLInputElement | null>(null)
const botonNuevo = ref<HTMLButtonElement | null>(null)

const editando = computed(() => modo.value === 'crear' || modo.value === 'renombrar')
const textoEnviar = computed(() => {
  if (modo.value === 'crear') return enviando.value ? 'Creando…' : 'Crear casete'
  return enviando.value ? 'Guardando…' : 'Guardar nombre'
})

async function abrir(nuevoModo: 'crear' | 'renombrar'): Promise<void> {
  modo.value = nuevoModo
  nombre.value = nuevoModo === 'renombrar' ? (activo.value?.name ?? '') : ''
  errorCampo.value = ''
  await nextTick()
  campo.value?.focus()
  campo.value?.select()
}

async function cerrar(): Promise<void> {
  modo.value = 'reposo'
  errorCampo.value = ''
  await nextTick()
  botonNuevo.value?.focus()
}

async function enviar(): Promise<void> {
  if (enviando.value) return
  const limpio = nombre.value.trim()
  if (!limpio) {
    errorCampo.value = 'Escribe un nombre para el casete.'
    return
  }
  if (limpio.length > MAX_NOMBRE) {
    errorCampo.value = `El nombre puede tener hasta ${MAX_NOMBRE} caracteres.`
    return
  }
  enviando.value = true
  errorCampo.value = ''
  try {
    if (modo.value === 'crear') await crear(limpio)
    else await renombrar(limpio)
    await cerrar()
  } catch (e) {
    errorCampo.value = e instanceof ApiError ? e.message : 'No pudimos guardar el casete. Vuelve a intentarlo.'
  } finally {
    enviando.value = false
  }
}

async function confirmarBorrado(): Promise<void> {
  enviando.value = true
  try {
    await eliminar()
  } finally {
    enviando.value = false
    await cerrar()
  }
}
</script>

<template>
  <section class="estante" aria-labelledby="titulo-estante">
    <h3 id="titulo-estante" class="visualmente-oculto">Tus casetes</h3>

    <ul v-if="cargando && casetes.length === 0" class="estante__fila" aria-label="Cargando casetes…">
      <li v-for="n in 3" :key="n" class="estante__lomo estante__lomo--esqueleto" aria-hidden="true" />
    </ul>

    <template v-else>
      <p v-if="casetes.length === 0 && !editando" class="estante__vacio">
        Aún no tienes casetes. Crea el primero con «Nuevo casete».
      </p>

      <ul class="estante__fila">
        <li v-for="casete in casetes" :key="casete.id">
          <button
            type="button"
            class="estante__lomo"
            :aria-pressed="activo?.id === casete.id"
            :title="casete.name"
            @click="seleccionar(casete.id)"
          >
            <span class="estante__nombre">{{ casete.name }}</span>
          </button>
        </li>
        <li v-if="modo !== 'crear'">
          <button ref="botonNuevo" type="button" class="estante__lomo estante__lomo--nuevo" @click="abrir('crear')">
            <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
              <path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="3" stroke-linecap="round" />
            </svg>
            Nuevo casete
          </button>
        </li>
      </ul>
    </template>

    <form v-if="editando" class="estante__form" novalidate @submit.prevent="enviar" @keydown.esc.prevent="cerrar">
      <label for="estante-nombre">Nombre del casete</label>
      <input
        id="estante-nombre"
        ref="campo"
        v-model="nombre"
        type="text"
        :maxlength="MAX_NOMBRE"
        autocomplete="off"
        :aria-invalid="!!errorCampo"
        :aria-describedby="errorCampo ? 'estante-error' : undefined"
      />
      <p v-if="errorCampo" id="estante-error" class="estante__error">{{ errorCampo }}</p>
      <div class="estante__botones">
        <button type="submit" class="boton-contorno" :disabled="enviando" :aria-busy="enviando || undefined">
          {{ textoEnviar }}
        </button>
        <button type="button" class="boton-contorno" @click="cerrar">Cancelar</button>
      </div>
    </form>

    <div v-else-if="modo === 'borrar' && activo" class="estante__confirmar" role="group" aria-labelledby="estante-pregunta">
      <p id="estante-pregunta">¿Borrar «{{ activo.name }}»? Esta acción no se puede deshacer.</p>
      <div class="estante__botones">
        <button type="button" class="boton-contorno boton-contorno--peligro" :disabled="enviando" @click="confirmarBorrado">
          Borrar casete
        </button>
        <button type="button" class="boton-contorno" @click="cerrar">Cancelar</button>
      </div>
    </div>

    <div v-else-if="activo" class="estante__botones">
      <button type="button" class="boton-contorno" @click="abrir('renombrar')">Renombrar</button>
      <button type="button" class="boton-contorno" @click="modo = 'borrar'">Borrar casete</button>
    </div>
  </section>
</template>

<style scoped>
.estante {
  display: grid;
  gap: var(--space-3);
  color: var(--deck-ink);
}

.estante__fila {
  display: flex;
  gap: var(--space-2);
  margin: 0;
  /* Deja espacio al contorno del casete activo y al anillo de foco dentro del scroll. */
  padding: var(--space-2);
  overflow-x: auto;
  list-style: none;
}

.estante__fila > li {
  flex: none;
}

.estante__lomo {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  max-width: 180px;
  min-height: 40px;
  padding: 0 var(--space-3);
  overflow: hidden;
  border: 0;
  border-radius: var(--radius-s);
  background: var(--tape);
  box-shadow: inset 0 -4px 0 rgb(0 0 0 / 0.2);
  color: var(--deck-ink);
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
}

.estante__nombre {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.estante__lomo[aria-pressed='true'] {
  outline: 2px solid var(--accent2);
  outline-offset: 2px;
}

.estante__lomo--nuevo {
  border: 2px dashed var(--deck-ink);
  background: transparent;
  box-shadow: none;
}

.estante__lomo--esqueleto {
  width: 96px;
  background: var(--rule-deck);
  box-shadow: none;
}

@media (hover: hover) {
  .estante__lomo:hover {
    filter: brightness(1.08);
  }
}

.estante__vacio,
.estante__confirmar p {
  margin: 0;
}

.estante__form {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-3);
  border-radius: var(--radius-m);
  background: var(--paper);
  color: var(--ink);
}

.estante__form label {
  font-size: 13px;
  font-weight: 500;
}

.estante__form input {
  width: 100%;
  min-width: 0;
  min-height: 44px;
  padding: 0 var(--space-3);
  border: 2px solid var(--ink);
  border-radius: var(--radius-s);
  background: var(--paper);
}

.estante__form input[aria-invalid='true'] {
  border-color: var(--danger);
}

.estante__error {
  margin: 0;
  color: var(--danger);
  font-size: 13px;
}

.estante__botones {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
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
  .boton-contorno:not(:disabled):hover {
    background: color-mix(in srgb, currentColor 12%, transparent);
  }
}

.estante__confirmar {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-3);
  border-radius: var(--radius-m);
  background: var(--paper);
  color: var(--ink);
}

.boton-contorno--peligro {
  color: var(--danger);
}

@media (max-width: 899px) {
  .estante__fila {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    overflow-x: visible;
  }

  .estante__lomo {
    width: 100%;
    max-width: none;
  }
}
</style>
