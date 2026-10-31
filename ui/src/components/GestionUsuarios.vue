<script setup lang="ts">
// Lista de usuarios con buscador por correo y cambio de rol (PATCH /api/users/{id}/role).
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { ApiError } from '../api/http'
import type { Role, UserOut } from '../api/types'
import * as users from '../api/users'
import { useAvisos } from '../composables/useAvisos'
import { useSession } from '../composables/useSession'
import AvisoEnLinea from './AvisoEnLinea.vue'

const ESPERA_MS = 250
const FILAS_ESQUELETO = 4

const { user: yo } = useSession()
const { mostrar } = useAvisos()

const busqueda = ref('')
const buscado = ref('')
const lista = ref<UserOut[]>([])
const cargando = ref(true)
const error = ref('')
const ocupados = ref<ReadonlySet<string>>(new Set())

let temporizador: ReturnType<typeof setTimeout> | undefined
let peticion = 0

function marcar(id: string, activo: boolean): void {
  const nuevos = new Set(ocupados.value)
  if (activo) nuevos.add(id)
  else nuevos.delete(id)
  ocupados.value = nuevos
}

async function buscar(): Promise<void> {
  const q = busqueda.value.trim()
  const mia = ++peticion
  cargando.value = true
  error.value = ''
  try {
    const resultado = await users.list(q)
    if (mia !== peticion) return
    lista.value = resultado
    buscado.value = q
  } catch (e) {
    if (mia !== peticion) return
    lista.value = []
    error.value =
      e instanceof ApiError ? e.message : 'No pudimos cargar los usuarios. Vuelve a intentarlo.'
  } finally {
    if (mia === peticion) cargando.value = false
  }
}

function onInput(): void {
  clearTimeout(temporizador)
  temporizador = setTimeout(() => void buscar(), ESPERA_MS)
}

async function cambiarRol(usuario: UserOut): Promise<void> {
  if (ocupados.value.has(usuario.id)) return
  const rol: Role = usuario.role === 'admin' ? 'listener' : 'admin'
  marcar(usuario.id, true)
  try {
    const actualizado = await users.setRole(usuario.id, rol)
    lista.value = lista.value.map((u) => (u.id === actualizado.id ? actualizado : u))
    mostrar(
      actualizado.role === 'admin'
        ? `${actualizado.name} ahora es admin`
        : `${actualizado.name} ya no es admin`,
    )
  } catch (e) {
    mostrar(
      e instanceof ApiError ? e.message : 'No pudimos cambiar el rol. Vuelve a intentarlo.',
      'error',
    )
  } finally {
    marcar(usuario.id, false)
  }
}

onMounted(() => void buscar())
onBeforeUnmount(() => clearTimeout(temporizador))
</script>

<template>
  <section class="usuarios" aria-labelledby="titulo-usuarios">
    <h2 id="titulo-usuarios">Usuarios</h2>

    <div class="usuarios__buscador">
      <input
        v-model="busqueda"
        type="search"
        placeholder="Buscar por correo"
        aria-label="Buscar por correo"
        autocomplete="off"
        @input="onInput"
      />
    </div>

    <ul v-if="cargando" class="usuarios__lista" aria-label="Cargando usuarios…">
      <li v-for="n in FILAS_ESQUELETO" :key="n" class="usuarios__esqueleto" aria-hidden="true"><span /><span /></li>
    </ul>

    <AvisoEnLinea v-else-if="error" reintentar @reintentar="buscar">{{ error }}</AvisoEnLinea>

    <p v-else-if="lista.length === 0" class="usuarios__vacio">
      {{ buscado ? `No encontramos usuarios con «${buscado}».` : 'Todavía no hay usuarios.' }}
    </p>

    <ul v-else class="usuarios__lista">
      <li v-for="usuario in lista" :key="usuario.id" class="usuarios__fila">
        <div class="usuarios__textos">
          <span class="usuarios__nombre" :title="usuario.name">{{ usuario.name }}</span>
          <span class="usuarios__detalle" :title="usuario.email">{{ usuario.email }}</span>
        </div>
        <span class="usuarios__rol">{{ usuario.role === 'admin' ? 'Admin' : 'Oyente' }}</span>
        <button
          v-if="usuario.id !== yo?.id"
          type="button"
          class="boton-contorno"
          :disabled="ocupados.has(usuario.id)"
          :aria-label="`${usuario.role === 'admin' ? 'Quitar admin a' : 'Hacer admin a'} ${usuario.name}`"
          @click="cambiarRol(usuario)"
        >
          {{ usuario.role === 'admin' ? 'Quitar admin' : 'Hacer admin' }}
        </button>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.usuarios {
  display: grid;
  gap: var(--space-4);
  align-content: start;
}

.usuarios__buscador input {
  width: 100%;
  min-height: 44px;
  padding: 0 var(--space-4);
  border: 2px solid var(--ink);
  border-radius: 999px;
  background: var(--paper);
}

.usuarios__lista {
  margin: 0;
  padding: 0;
  list-style: none;
}

.usuarios__fila {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--rule);
}

.usuarios__textos {
  display: grid;
  min-width: 0;
}

.usuarios__nombre,
.usuarios__detalle {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.usuarios__nombre {
  font-weight: 700;
}

.usuarios__detalle {
  font-size: 13px;
  opacity: 0.8;
}

.usuarios__rol {
  font-size: 13px;
  font-weight: 500;
}

.usuarios__vacio {
  margin: 0;
}

.usuarios__esqueleto {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--rule);
}

.usuarios__esqueleto span {
  height: 12px;
  border-radius: var(--radius-s);
  background: var(--rule);
}

.usuarios__esqueleto span:first-child {
  width: 45%;
}

.usuarios__esqueleto span:last-child {
  width: 30%;
}

@media (max-width: 599px) {
  .usuarios__fila {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .usuarios__fila .boton-contorno {
    grid-column: 1 / -1;
    justify-self: start;
  }
}
</style>
