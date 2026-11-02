<script setup lang="ts">
// Catálogo para administradores: búsqueda, edición en línea y retiro (DELETE = baja lógica).
import { onMounted, reactive, ref } from 'vue'
import { ApiError } from '../api/http'
import * as songs from '../api/songs'
import type { SongOut } from '../api/types'
import { useAvisos } from '../composables/useAvisos'
import { useBusqueda, useOcupados } from '../composables/useBusqueda'
import AvisoEnLinea from './AvisoEnLinea.vue'
import Portada from './Portada.vue'
import Icono from './icons/Icono.vue'

const FILAS_ESQUELETO = 4
const PORTADA_MAX_BYTES = 2 * 1024 * 1024

const emit = defineEmits<{ cambio: [] }>()
const { mostrar } = useAvisos()

const canciones = ref<SongOut[]>([])
const total = ref(0)
const cargandoMas = ref(false)

const editando = ref<string | null>(null)
const borrador = reactive({ title: '', artist: '', album: '' })
const errorEdicion = ref('')
const { ocupados: ocupadas, marcar } = useOcupados()
// Las portadas se sirven con caché de un día: tras cambiarla se pide con ?v= nuevo.
const versiones = reactive<Record<string, number>>({})

function portadaDe(cancion: SongOut): string | null {
  if (!cancion.has_cover) return null
  const v = versiones[cancion.id]
  return v ? `${songs.coverUrl(cancion.id)}?v=${v}` : songs.coverUrl(cancion.id)
}

async function cambiarPortada(cancion: SongOut, evento: Event): Promise<void> {
  const input = evento.target as HTMLInputElement
  const imagen = input.files?.[0]
  input.value = ''
  if (!imagen || ocupadas.value.has(cancion.id)) return
  if (imagen.size > PORTADA_MAX_BYTES) {
    mostrar('La portada debe pesar 2 MB o menos.', 'error')
    return
  }
  marcar(cancion.id, true)
  try {
    const actualizada = await songs.uploadCover(cancion.id, imagen)
    versiones[cancion.id] = Date.now()
    canciones.value = canciones.value.map((c) => (c.id === actualizada.id ? actualizada : c))
    mostrar(`Portada de «${cancion.title}» actualizada`)
  } catch (e) {
    mostrar(mensajeDe(e, 'No pudimos subir la portada. Vuelve a intentarlo.'), 'error')
  } finally {
    marcar(cancion.id, false)
  }
}

const { busqueda, buscado, cargando, error, buscar, alEscribir, token, esVigente } = useBusqueda({
  consultar: (q) => songs.list(q, 0),
  aplicar: (pagina) => {
    canciones.value = pagina.items
    total.value = pagina.total
  },
  alFallar: () => {
    canciones.value = []
    total.value = 0
  },
  mensajeError: 'No pudimos cargar las canciones. Vuelve a intentarlo.',
})

function mensajeDe(e: unknown, respaldo: string): string {
  return e instanceof ApiError ? e.message : respaldo
}

async function cargarMas(): Promise<void> {
  const mia = token()
  cargandoMas.value = true
  error.value = ''
  try {
    const pagina = await songs.list(buscado.value, canciones.value.length)
    if (!esVigente(mia)) return
    canciones.value = [...canciones.value, ...pagina.items]
    total.value = pagina.total
  } catch (e) {
    if (esVigente(mia)) error.value = mensajeDe(e, 'No pudimos cargar más canciones.')
  } finally {
    cargandoMas.value = false
  }
}

/** Agrega una canción recién subida al principio, sin recargar la lista. */
function agregar(cancion: SongOut): void {
  if (canciones.value.some((c) => c.id === cancion.id)) return
  canciones.value = [cancion, ...canciones.value]
  total.value += 1
}

function editar(cancion: SongOut): void {
  editando.value = cancion.id
  borrador.title = cancion.title
  borrador.artist = cancion.artist
  borrador.album = cancion.album
  errorEdicion.value = ''
}

function cancelar(): void {
  editando.value = null
  errorEdicion.value = ''
}

async function guardar(cancion: SongOut): Promise<void> {
  if (ocupadas.value.has(cancion.id)) return
  const datos = {
    title: borrador.title.trim(),
    artist: borrador.artist.trim(),
    album: borrador.album.trim(),
  }
  if (!datos.title || !datos.artist || !datos.album) {
    errorEdicion.value = 'Título, artista y álbum no pueden quedar vacíos.'
    return
  }
  marcar(cancion.id, true)
  errorEdicion.value = ''
  try {
    const actualizada = await songs.update(cancion.id, datos)
    canciones.value = canciones.value.map((c) => (c.id === actualizada.id ? actualizada : c))
    editando.value = null
    mostrar('Cambios guardados')
  } catch (e) {
    errorEdicion.value = mensajeDe(e, 'No pudimos guardar los cambios. Vuelve a intentarlo.')
  } finally {
    marcar(cancion.id, false)
  }
}

async function retirar(cancion: SongOut): Promise<void> {
  if (ocupadas.value.has(cancion.id)) return
  if (!window.confirm(`¿Retirar «${cancion.title}» del catálogo? Los oyentes dejarán de verla.`)) return
  marcar(cancion.id, true)
  try {
    await songs.deactivate(cancion.id)
    canciones.value = canciones.value.filter((c) => c.id !== cancion.id)
    total.value = Math.max(0, total.value - 1)
    if (editando.value === cancion.id) cancelar()
    mostrar(`«${cancion.title}» salió del catálogo`)
    emit('cambio')
  } catch (e) {
    mostrar(mensajeDe(e, 'No pudimos retirar la canción. Vuelve a intentarlo.'), 'error')
  } finally {
    marcar(cancion.id, false)
  }
}

onMounted(() => void buscar())
defineExpose({ agregar })
</script>

<template>
  <section class="tabla" aria-labelledby="titulo-tabla">
    <h2 id="titulo-tabla">Canciones</h2>

    <div class="busqueda-pildora">
      <input
        v-model="busqueda"
        type="search"
        placeholder="Buscar canción, artista o álbum"
        aria-label="Buscar canción, artista o álbum"
        autocomplete="off"
        @input="alEscribir"
      />
    </div>

    <ul v-if="cargando" class="tabla__lista" aria-label="Cargando canciones…">
      <li v-for="n in FILAS_ESQUELETO" :key="n" class="esqueleto-fila" aria-hidden="true"><span /><span /></li>
    </ul>

    <AvisoEnLinea v-else-if="error && canciones.length === 0" reintentar @reintentar="buscar">
      {{ error }}
    </AvisoEnLinea>

    <p v-else-if="canciones.length === 0" class="tabla__vacio">
      {{ buscado ? `No encontramos canciones con «${buscado}».` : 'Todavía no hay canciones en el catálogo.' }}
    </p>

    <template v-else>
      <ul class="tabla__lista">
        <li v-for="cancion in canciones" :key="cancion.id" class="tabla__fila">
          <form
            v-if="editando === cancion.id"
            class="tabla__edicion"
            novalidate
            @submit.prevent="guardar(cancion)"
          >
            <div class="campo">
              <label :for="`editar-titulo-${cancion.id}`">Título</label>
              <input :id="`editar-titulo-${cancion.id}`" v-model="borrador.title" type="text" maxlength="200" />
            </div>
            <div class="campo">
              <label :for="`editar-artista-${cancion.id}`">Artista</label>
              <input :id="`editar-artista-${cancion.id}`" v-model="borrador.artist" type="text" maxlength="200" />
            </div>
            <div class="campo">
              <label :for="`editar-album-${cancion.id}`">Álbum</label>
              <input :id="`editar-album-${cancion.id}`" v-model="borrador.album" type="text" maxlength="200" />
            </div>
            <p v-if="errorEdicion" class="campo__error" role="alert">{{ errorEdicion }}</p>
            <div class="tabla__acciones">
              <button type="submit" class="boton-contorno" :disabled="ocupadas.has(cancion.id)">Guardar</button>
              <button type="button" class="boton-contorno" @click="cancelar">Cancelar</button>
            </div>
          </form>

          <template v-else>
            <Portada :src="portadaDe(cancion)" :titulo="cancion.title" :tam="40" />
            <div class="tabla__textos">
              <span class="tabla__titulo" :title="cancion.title">{{ cancion.title }}</span>
              <span class="tabla__detalle" :title="`${cancion.artist} · ${cancion.album}`">
                {{ cancion.artist }} · {{ cancion.album }}
              </span>
            </div>
            <div class="tabla__acciones">
              <label class="boton-contorno tabla__portada" :class="{ 'tabla__portada--ocupada': ocupadas.has(cancion.id) }">
                <Icono nombre="image" :tam="14" /> Cambiar portada
                <input
                  class="visualmente-oculto"
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  :aria-label="`Cambiar portada de «${cancion.title}»`"
                  :disabled="ocupadas.has(cancion.id)"
                  @change="cambiarPortada(cancion, $event)"
                />
              </label>
              <button
                type="button"
                class="boton-contorno"
                :aria-label="`Editar «${cancion.title}»`"
                @click="editar(cancion)"
              >
                Editar
              </button>
              <button
                type="button"
                class="boton-contorno tabla__retirar"
                :disabled="ocupadas.has(cancion.id)"
                :aria-label="`Retirar «${cancion.title}» del catálogo`"
                @click="retirar(cancion)"
              >
                Retirar del catálogo
              </button>
            </div>
          </template>
        </li>
      </ul>

      <AvisoEnLinea v-if="error" reintentar @reintentar="cargarMas">{{ error }}</AvisoEnLinea>

      <button
        v-if="canciones.length < total"
        type="button"
        class="boton-contorno tabla__mas"
        :disabled="cargandoMas"
        :aria-busy="cargandoMas || undefined"
        @click="cargarMas"
      >
        {{ cargandoMas ? 'Cargando canciones…' : 'Cargar más' }}
      </button>
    </template>
  </section>
</template>

<style scoped>
.tabla__portada {
  cursor: pointer;
}

.tabla__portada:focus-within {
  outline: 2px solid var(--focus);
  outline-offset: 2px;
}

.tabla__portada--ocupada {
  opacity: 0.45;
  cursor: progress;
}

.tabla {
  display: grid;
  gap: var(--space-4);
  align-content: start;
}

.tabla__lista {
  margin: 0;
  padding: 0;
  list-style: none;
}

.tabla__fila {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--rule);
}

.tabla__textos {
  display: grid;
  min-width: 0;
}

.tabla__titulo,
.tabla__detalle {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tabla__titulo {
  font-weight: 700;
}

.tabla__detalle {
  font-size: 13px;
  opacity: 0.8;
}

.tabla__acciones {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.tabla__retirar {
  color: var(--danger);
}

.tabla__edicion {
  display: grid;
  gap: var(--space-3);
}

.tabla__vacio {
  margin: 0;
}

.tabla__mas {
  justify-self: center;
  padding: 0 var(--space-5);
}

@media (min-width: 600px) {
  .tabla__fila:not(:has(form)) {
    grid-template-columns: 1fr auto;
    align-items: center;
    gap: var(--space-3);
  }
}
</style>
