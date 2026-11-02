<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ApiError } from '../api/http'
import * as playlists from '../api/playlists'
import type { PlaylistDetail } from '../api/types'
import AvisoEnLinea from '../components/AvisoEnLinea.vue'
import CabeceraCasete from '../components/CabeceraCasete.vue'
import CompartirCasete from '../components/CompartirCasete.vue'
import FilaCancion from '../components/FilaCancion.vue'
import Portada from '../components/Portada.vue'
import Icono from '../components/icons/Icono.vue'
import { desdeCasete, resumenDuracion } from '../composables/canciones'
import { useAvisos } from '../composables/useAvisos'
import { useCasetes } from '../composables/useCasetes'
import { usePlayer } from '../composables/usePlayer'
import { useSession } from '../composables/useSession'

// Detalle de un casete: escuchar, ordenar, quitar, portada, nombre, compartir y miembros.
const IMAGEN_MAX_BYTES = 2 * 1024 * 1024
const MAX_NOMBRE = 80

const route = useRoute()
const router = useRouter()
const player = usePlayer()
const casetes = useCasetes()
const { mostrar } = useAvisos()
const { user } = useSession()

const casete = ref<PlaylistDetail | null>(null)
const cargando = ref(true)
const error = ref('')
const ocupado = ref(false)
const renombrando = ref(false)
const nombreNuevo = ref('')
const confirmarBorrado = ref(false)
const versionPortada = ref(0)
const arrastrando = ref<number | null>(null)

const id = computed(() => String(route.params.id ?? ''))
const esDueno = computed(() => casete.value?.role === 'owner')
const canciones = computed(() => casete.value?.songs.map(desdeCasete) ?? [])
const reproducibles = computed(() => canciones.value.filter((c) => c.is_active))
const portada = computed(() =>
  casete.value?.has_cover ? `${playlists.coverUrl(casete.value.id)}?v=${versionPortada.value}` : null,
)
const detalle = computed(() =>
  casete.value ? resumenDuracion(casete.value.songs.length, casete.value.total_seconds) : '',
)

function mensajeDe(e: unknown): string {
  return e instanceof ApiError ? e.message : 'Algo salió mal. Vuelve a intentarlo.'
}

const perdioAcceso = (e: unknown) =>
  e instanceof ApiError && e.status === 404 && e.code === 'playlist_not_found'

/** Sin acceso (borrado o te quitaron): se avisa, se recarga la biblioteca y se va a Inicio. */
async function salirPorFaltaDeAcceso(): Promise<void> {
  mostrar('Ya no tienes acceso a este casete.', 'error')
  casetes.olvidar(id.value)
  void casetes.cargar()
  await router.push('/')
}

async function fallo(e: unknown): Promise<void> {
  if (perdioAcceso(e)) await salirPorFaltaDeAcceso()
  else mostrar(mensajeDe(e), 'error')
}

function aplicar(nuevo: PlaylistDetail): void {
  casete.value = nuevo
  casetes.sincronizar(nuevo)
}

/** Ejecuta una mutación de una en una; los errores pasan por `fallo`. */
async function ejecutar<T>(accion: () => Promise<T>): Promise<T | undefined> {
  if (ocupado.value) return undefined
  ocupado.value = true
  try {
    return await accion()
  } catch (e) {
    await fallo(e)
    return undefined
  } finally {
    ocupado.value = false
  }
}

async function cargar(): Promise<void> {
  const pedido = id.value
  cargando.value = true
  error.value = ''
  renombrando.value = false
  confirmarBorrado.value = false
  try {
    const recibido = await playlists.get(pedido)
    if (pedido === id.value) aplicar(recibido)
  } catch (e) {
    if (pedido !== id.value) return
    if (perdioAcceso(e)) await salirPorFaltaDeAcceso()
    else error.value = mensajeDe(e)
  } finally {
    if (pedido === id.value) cargando.value = false
  }
}
watch(id, cargar, { immediate: true })

function reproducirTodo(): void {
  const [primera] = reproducibles.value
  if (primera) void player.play(primera, reproducibles.value)
}

function reproducir(indice: number): void {
  const cancion = canciones.value[indice]
  if (cancion?.is_active) void player.play(cancion, reproducibles.value)
}

async function quitar(songId: string): Promise<void> {
  const nuevo = await ejecutar(() => playlists.removeSong(id.value, songId))
  if (nuevo) aplicar(nuevo)
}

async function mover(desde: number, hacia: number): Promise<void> {
  const actual = casete.value
  if (!actual || desde === hacia || hacia < 0 || hacia >= actual.songs.length) return
  const ids = actual.songs.map((s) => s.song_id)
  const [movida] = ids.splice(desde, 1)
  ids.splice(hacia, 0, movida)
  const nuevo = await ejecutar(() => playlists.reorder(actual.id, ids))
  if (nuevo) aplicar(nuevo)
}

function onDrop(hacia: number): void {
  if (arrastrando.value !== null) void mover(arrastrando.value, hacia)
  arrastrando.value = null
}

function empezarRenombrar(): void {
  nombreNuevo.value = casete.value?.name ?? ''
  renombrando.value = true
}

async function guardarNombre(): Promise<void> {
  const limpio = nombreNuevo.value.trim()
  const actual = casete.value
  if (!actual) return
  if (!limpio) {
    mostrar('Escribe un nombre para el casete.', 'error')
    return
  }
  if (limpio === actual.name) {
    renombrando.value = false
    return
  }
  const resumen = await ejecutar(() => playlists.rename(actual.id, limpio))
  if (resumen && casete.value?.id === resumen.id) {
    aplicar({ ...casete.value, name: resumen.name })
    renombrando.value = false
  }
}

function onTeclaNombre(evento: KeyboardEvent): void {
  if (evento.key === 'Enter') void guardarNombre()
  else if (evento.key === 'Escape') renombrando.value = false
}

async function cambiarPortada(evento: Event): Promise<void> {
  const input = evento.target as HTMLInputElement
  const archivo = input.files?.[0]
  input.value = ''
  const actual = casete.value
  if (!archivo || !actual) return
  if (archivo.size > IMAGEN_MAX_BYTES) {
    mostrar('La portada debe pesar 2 MB o menos.', 'error')
    return
  }
  const resumen = await ejecutar(() => playlists.uploadCover(actual.id, archivo))
  if (resumen && casete.value?.id === resumen.id) {
    versionPortada.value = Date.now()
    aplicar({ ...casete.value, has_cover: true })
    mostrar('Portada actualizada.', 'info')
  }
}

async function borrar(): Promise<void> {
  const actual = casete.value
  if (!actual) return
  const hecho = await ejecutar(async () => {
    await playlists.remove(actual.id)
    return true
  })
  if (!hecho) return
  casetes.olvidar(actual.id)
  mostrar(`Borraste «${actual.name}».`, 'info')
  await router.push('/')
}

async function quitarMiembro(userId: string): Promise<void> {
  const actual = casete.value
  if (!actual) return
  const saliendo = userId === user.value?.id
  const hecho = await ejecutar(async () => {
    await playlists.removeMember(actual.id, userId)
    return true
  })
  if (!hecho) return
  if (saliendo) {
    casetes.olvidar(actual.id)
    mostrar(`Saliste de «${actual.name}».`, 'info')
    await router.push('/')
  } else if (casete.value) {
    casete.value = { ...casete.value, members: casete.value.members.filter((m) => m.user_id !== userId) }
  }
}
</script>

<template>
  <section class="casete" aria-labelledby="titulo-casete">
    <div v-if="cargando && !casete" class="esqueleto-fila" aria-hidden="true"><span /><span /></div>
    <AvisoEnLinea v-else-if="error" reintentar @reintentar="cargar">{{ error }}</AvisoEnLinea>

    <template v-else-if="casete">
      <CabeceraCasete
        :antetitulo="esDueno ? 'CASETE' : 'CASETE COLABORATIVO'"
        :detalle="detalle"
      >
        <template #portada>
          <Portada :src="portada" :titulo="casete.name" :tam="160" radio="m" />
          <label v-if="esDueno" class="casete__portada-boton boton-contorno">
            <Icono nombre="image" :tam="14" /> Cambiar portada
            <input
              class="visualmente-oculto"
              type="file"
              accept="image/png,image/jpeg,image/webp"
              :disabled="ocupado"
              @change="cambiarPortada"
            />
          </label>
        </template>

        <template #titulo>
          <div v-if="renombrando" class="casete__renombrar">
            <input
              v-model="nombreNuevo"
              class="casete__campo-nombre"
              type="text"
              :maxlength="MAX_NOMBRE"
              aria-label="Nombre del casete"
              @keydown="onTeclaNombre"
            />
            <button type="button" class="boton-principal" :disabled="ocupado" @click="guardarNombre">
              Guardar
            </button>
            <button type="button" class="boton-texto boton-texto--secundario" @click="renombrando = false">
              Cancelar
            </button>
          </div>
          <div v-else class="casete__nombre">
            <h1 id="titulo-casete">{{ casete.name }}</h1>
            <button
              v-if="esDueno"
              type="button"
              class="boton-icono"
              aria-label="Renombrar casete"
              @click="empezarRenombrar"
            >
              <Icono nombre="pencil" :tam="16" />
            </button>
          </div>
        </template>

        <template #acciones>
          <button
            type="button"
            class="boton-principal"
            data-prueba="reproducir-todo"
            :disabled="reproducibles.length === 0"
            @click="reproducirTodo"
          >
            <Icono nombre="play" :tam="14" /> Reproducir todo
          </button>
          <button
            v-if="!esDueno"
            type="button"
            class="boton-contorno"
            data-prueba="salir-casete"
            :disabled="ocupado || !user"
            @click="user && quitarMiembro(user.id)"
          >
            <Icono nombre="log-out" :tam="14" /> Salir del casete
          </button>
          <template v-if="esDueno">
            <span v-if="confirmarBorrado" class="casete__confirmar" role="group" aria-label="Confirmar borrado">
              <span>¿Borrar «{{ casete.name }}»? No se puede deshacer.</span>
              <button type="button" class="boton-contorno boton-peligro" :disabled="ocupado" @click="borrar">
                Borrar
              </button>
              <button type="button" class="boton-texto boton-texto--secundario" @click="confirmarBorrado = false">
                Cancelar
              </button>
            </span>
            <button
              v-else
              type="button"
              class="boton-texto boton-peligro"
              data-prueba="borrar-casete"
              @click="confirmarBorrado = true"
            >
              <Icono nombre="trash-2" :tam="14" /> Borrar casete
            </button>
          </template>
        </template>
      </CabeceraCasete>

      <p v-if="casete.songs.length === 0" class="texto-secundario">
        Este casete está vacío. Graba canciones desde el <RouterLink to="/catalogo">Catálogo</RouterLink>.
      </p>
      <ol v-else class="casete__lista">
        <li
          v-for="(fila, i) in casete.songs"
          :key="fila.song_id"
          class="casete__item"
          :class="{ 'casete__item--arrastrando': arrastrando === i }"
          draggable="true"
          @dragstart="arrastrando = i"
          @dragend="arrastrando = null"
          @dragover.prevent
          @drop.prevent="onDrop(i)"
        >
          <span class="casete__asa" aria-hidden="true"><Icono nombre="grip-vertical" :tam="16" /></span>
          <FilaCancion
            class="casete__fila"
            :cancion="canciones[i]"
            :disponible="fila.status !== 'unavailable'"
            :sonando="player.current.value?.id === fila.song_id"
            @reproducir="reproducir(i)"
          >
            <template #acciones>
              <button
                type="button"
                class="boton-icono"
                :aria-label="`Subir «${fila.title}»`"
                :disabled="i === 0 || ocupado"
                @click="mover(i, i - 1)"
              >
                <Icono nombre="arrow-up" :tam="16" />
              </button>
              <button
                type="button"
                class="boton-icono"
                :aria-label="`Bajar «${fila.title}»`"
                :disabled="i === casete.songs.length - 1 || ocupado"
                @click="mover(i, i + 1)"
              >
                <Icono nombre="arrow-down" :tam="16" />
              </button>
              <button
                type="button"
                class="boton-icono"
                :aria-label="`Quitar «${fila.title}» del casete`"
                :disabled="ocupado"
                @click="quitar(fila.song_id)"
              >
                <Icono nombre="x" :tam="16" />
              </button>
            </template>
          </FilaCancion>
        </li>
      </ol>

      <div class="casete__extras">
        <section class="tarjeta casete__miembros" aria-labelledby="titulo-miembros">
          <h2 id="titulo-miembros" class="casete__subtitulo">
            <Icono nombre="users" :tam="18" /> Miembros
          </h2>
          <p v-if="casete.members.length === 0" class="texto-secundario">
            {{ esDueno ? 'Aún no invitas a nadie.' : 'Solo tú y quien te invitó.' }}
          </p>
          <ul v-else class="casete__lista-miembros">
            <li v-for="m in casete.members" :key="m.user_id">
              <span>{{ m.name }}<template v-if="m.user_id === user?.id"> (tú)</template></span>
              <button
                v-if="esDueno"
                type="button"
                class="boton-texto boton-texto--secundario"
                :aria-label="`Quitar a ${m.name} del casete`"
                :disabled="ocupado"
                @click="quitarMiembro(m.user_id)"
              >
                Quitar
              </button>
            </li>
          </ul>
        </section>
        <CompartirCasete v-if="esDueno" :casete-id="casete.id" @fallo="fallo" />
      </div>
    </template>
  </section>
</template>

<style scoped>
.casete {
  display: grid;
  gap: var(--space-5);
  padding: var(--space-5);
}

.casete__portada-boton {
  position: absolute;
  right: var(--space-2);
  bottom: var(--space-2);
  left: var(--space-2);
  background: var(--overlay);
  font-size: 11px;
}

.casete__portada-boton:focus-within {
  outline: 2px solid var(--focus);
  outline-offset: 2px;
}

.casete__nombre,
.casete__renombrar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.casete__campo-nombre {
  min-width: 0;
  min-height: 40px;
  padding: 0 var(--space-3);
  border: 1px solid var(--surface);
  border-radius: var(--radius-m);
  background: var(--bg);
  color: var(--ink);
  font-family: var(--font-display);
  font-size: 22px;
}

.casete__confirmar {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}

.casete__lista {
  display: grid;
  gap: var(--space-1);
  margin: 0;
  padding: 0;
  list-style: none;
}

.casete__item {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.casete__item--arrastrando {
  opacity: 0.5;
}

.casete__asa {
  color: var(--ink-muted);
  cursor: grab;
}

.casete__fila {
  flex: 1;
  min-width: 0;
}

.casete__extras {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-4);
  align-items: start;
}

.casete__miembros {
  display: grid;
  gap: var(--space-3);
}

.casete__subtitulo {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 20px;
}

.casete__lista-miembros {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.casete__lista-miembros li {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

@media (max-width: 900px) {
  .casete {
    padding: var(--space-4);
  }

  .casete__extras {
    grid-template-columns: minmax(0, 1fr);
  }

  .casete__asa {
    display: none;
  }
}
</style>
