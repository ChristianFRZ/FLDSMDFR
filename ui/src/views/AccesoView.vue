<script setup lang="ts">
import { computed, nextTick, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ApiError } from '../api/http'
import { useSession } from '../composables/useSession'

type Pestana = 'entrar' | 'crear'

const PESTANAS: ReadonlyArray<{ id: Pestana; texto: string }> = [
  { id: 'entrar', texto: 'Entrar' },
  { id: 'crear', texto: 'Crear cuenta' },
]
const MIN_PASSWORD = 8
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const router = useRouter()
const session = useSession()

const pestana = ref<Pestana>('entrar')
const nombre = ref('')
const correo = ref('')
const password = ref('')
const verPassword = ref(false)
const enviando = ref(false)
const errorServidor = ref('')
const errores = reactive<{ nombre: string; correo: string; password: string }>({
  nombre: '',
  correo: '',
  password: '',
})

const esRegistro = computed(() => pestana.value === 'crear')
const textoBoton = computed(() => {
  if (enviando.value) return esRegistro.value ? 'Creando cuenta…' : 'Entrando…'
  return esRegistro.value ? 'Crear cuenta' : 'Entrar'
})

function limpiarErrores(): void {
  errores.nombre = ''
  errores.correo = ''
  errores.password = ''
  errorServidor.value = ''
}

function elegir(id: Pestana): void {
  pestana.value = id
  limpiarErrores()
}

function moverPestana(evento: KeyboardEvent): void {
  const actual = PESTANAS.findIndex((p) => p.id === pestana.value)
  let destino = actual
  if (evento.key === 'ArrowRight') destino = (actual + 1) % PESTANAS.length
  else if (evento.key === 'ArrowLeft') destino = (actual - 1 + PESTANAS.length) % PESTANAS.length
  else if (evento.key === 'Home') destino = 0
  else if (evento.key === 'End') destino = PESTANAS.length - 1
  else return
  evento.preventDefault()
  elegir(PESTANAS[destino].id)
  void nextTick(() => document.getElementById(`pestana-${PESTANAS[destino].id}`)?.focus())
}

function validar(): boolean {
  limpiarErrores()
  if (esRegistro.value && !nombre.value.trim()) errores.nombre = 'Escribe tu nombre.'
  if (!correo.value.trim()) errores.correo = 'Escribe tu correo.'
  else if (!EMAIL_RE.test(correo.value.trim())) errores.correo = 'Revisa que el correo tenga el formato nombre@dominio.mx.'
  if (!password.value) errores.password = 'Escribe tu contraseña.'
  else if (esRegistro.value && password.value.length < MIN_PASSWORD)
    errores.password = `Usa al menos ${MIN_PASSWORD} caracteres.`
  return !errores.nombre && !errores.correo && !errores.password
}

async function enviar(): Promise<void> {
  if (enviando.value || !validar()) return
  enviando.value = true
  try {
    if (esRegistro.value) await session.register(nombre.value.trim(), correo.value.trim(), password.value)
    else await session.login(correo.value.trim(), password.value)
    await router.push('/')
  } catch (error) {
    errorServidor.value =
      error instanceof ApiError ? error.message : 'Algo salió mal. Vuelve a intentarlo.'
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <section class="acceso" aria-labelledby="titulo-acceso">
    <div class="acceso__casete" aria-hidden="true">
      <span class="acceso__carrete"></span>
      <span class="acceso__etiqueta">FLDSMDFR</span>
      <span class="acceso__carrete"></span>
    </div>

    <div class="acceso__tarjeta">
      <h1 id="titulo-acceso" class="visualmente-oculto">Acceso a FLDSMDFR</h1>

      <div class="acceso__pestanas" role="tablist" aria-label="Acceso" @keydown="moverPestana">
        <button
          v-for="p in PESTANAS"
          :id="`pestana-${p.id}`"
          :key="p.id"
          type="button"
          role="tab"
          class="acceso__pestana"
          :aria-selected="pestana === p.id"
          aria-controls="panel-acceso"
          :tabindex="pestana === p.id ? 0 : -1"
          @click="elegir(p.id)"
        >
          {{ p.texto }}
        </button>
      </div>

      <div id="panel-acceso" role="tabpanel" :aria-labelledby="`pestana-${pestana}`">
        <p v-if="errorServidor" class="acceso__aviso" role="alert">
          <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
            <path d="M4 4l8 8M12 4l-8 8" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
          </svg>
          <span>{{ errorServidor }}</span>
        </p>

        <form class="acceso__form" novalidate @submit.prevent="enviar">
          <div v-if="esRegistro" class="campo">
            <label for="acceso-nombre">Nombre</label>
            <input
              id="acceso-nombre"
              v-model="nombre"
              type="text"
              autocomplete="name"
              maxlength="80"
              :class="{ 'campo--error': errores.nombre }"
              :aria-invalid="!!errores.nombre"
              :aria-describedby="errores.nombre ? 'error-nombre' : undefined"
            />
            <p v-if="errores.nombre" id="error-nombre" class="campo__error">{{ errores.nombre }}</p>
          </div>

          <div class="campo">
            <label for="acceso-correo">Correo</label>
            <input
              id="acceso-correo"
              v-model="correo"
              type="email"
              autocomplete="email"
              inputmode="email"
              :class="{ 'campo--error': errores.correo }"
              :aria-invalid="!!errores.correo"
              :aria-describedby="errores.correo ? 'error-correo' : undefined"
            />
            <p v-if="errores.correo" id="error-correo" class="campo__error">{{ errores.correo }}</p>
          </div>

          <div class="campo">
            <label for="acceso-password">Contraseña</label>
            <div class="campo__password">
              <input
                id="acceso-password"
                v-model="password"
                :type="verPassword ? 'text' : 'password'"
                :autocomplete="esRegistro ? 'new-password' : 'current-password'"
                :class="{ 'campo--error': errores.password }"
                :aria-invalid="!!errores.password"
                :aria-describedby="
                  errores.password ? 'error-password' : esRegistro ? 'ayuda-password' : undefined
                "
              />
              <button
                type="button"
                class="boton-contorno"
                :aria-pressed="verPassword"
                @click="verPassword = !verPassword"
              >
                {{ verPassword ? 'Ocultar' : 'Mostrar' }}
              </button>
            </div>
            <p v-if="errores.password" id="error-password" class="campo__error">{{ errores.password }}</p>
            <p v-else-if="esRegistro" id="ayuda-password" class="campo__ayuda">
              Mínimo {{ MIN_PASSWORD }} caracteres.
            </p>
          </div>

          <button type="submit" class="boton-principal" :disabled="enviando" :aria-busy="enviando">
            {{ textoBoton }}
          </button>
        </form>
      </div>
    </div>
  </section>
</template>

<style scoped>
.acceso {
  display: grid;
  gap: var(--space-5);
  justify-items: center;
  width: 100%;
  max-width: 420px;
  margin: 0 auto;
  padding: var(--space-4) var(--space-4) var(--space-5);
}

/* Casete grande: cuerpo --deck, etiqueta de papel con el nombre a mano y dos carretes. */
.acceso__casete {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  width: 100%;
  padding: var(--space-5) var(--space-4);
  border-radius: var(--radius-m);
  background: var(--deck);
}

.acceso__etiqueta {
  flex: 1;
  padding: var(--space-3) var(--space-2);
  border-radius: var(--radius-s);
  background: var(--paper);
  color: var(--ink);
  font-family: var(--font-hand);
  font-size: 36px;
  line-height: 1;
  text-align: center;
}

.acceso__carrete {
  flex: none;
  width: 36px;
  height: 36px;
  border: 6px solid var(--deck-ink);
  border-radius: 50%;
  opacity: 0.8;
}

.acceso__tarjeta {
  display: grid;
  gap: var(--space-4);
  width: 100%;
  padding: var(--space-4);
  border-radius: var(--radius-m);
  background: var(--paper);
  color: var(--ink);
}

.acceso__pestanas {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-2);
}

.acceso__pestana {
  min-height: 44px;
  border: 2px solid var(--ink);
  border-radius: 999px;
  background: transparent;
  font-weight: 500;
}

.acceso__pestana[aria-selected='true'] {
  background: var(--ink);
  color: var(--bg);
  font-weight: 700;
}

@media (hover: hover) {
  .acceso__pestana[aria-selected='false']:hover {
    background: color-mix(in srgb, currentColor 12%, transparent);
  }
}

.acceso__aviso {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  margin: 0 0 var(--space-4);
  padding: var(--space-3) var(--space-4);
  border-left: 4px solid var(--danger);
  border-radius: var(--radius-m);
  background: var(--bg);
  color: var(--ink);
}

.acceso__aviso svg {
  flex: none;
  margin-top: var(--space-1);
  color: var(--danger);
}

.acceso__form {
  display: grid;
  gap: var(--space-4);
}

.campo__password {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: var(--space-2);
}

/* Variantes de Acceso: botones algo más altos que los de base.css. */
.boton-contorno {
  min-height: 44px;
  font-size: 15px;
}

.acceso__pestana:active {
  transform: scale(0.96);
  transition: transform 80ms;
}
</style>
