<script setup lang="ts">
// Formulario de subida de canciones (DESIGN.md §7.3). Valida en el cliente antes de enviar.
import { reactive, ref } from 'vue'
import { ApiError } from '../api/http'
import * as songs from '../api/songs'
import type { SongOut } from '../api/types'
import { useAvisos } from '../composables/useAvisos'
import AvisoEnLinea from './AvisoEnLinea.vue'

const EXTENSIONES = ['.mp3', '.ogg', '.wav']
const MAX_BYTES = 20 * 1024 * 1024
const PORTADA_MAX_BYTES = 2 * 1024 * 1024
const TIPOS_PORTADA = ['image/png', 'image/jpeg', 'image/webp']

const MENSAJES_API: Record<string, string> = {
  invalid_audio: 'El archivo no es un audio válido.',
  unsupported_format: 'Formato no compatible. Usa MP3, OGG o WAV.',
  file_too_large: 'El archivo pesa más de 20 MB.',
}

const emit = defineEmits<{ subida: [song: SongOut] }>()
const { mostrar } = useAvisos()

const titulo = ref('')
const artista = ref('')
const album = ref('')
const archivo = ref<File | null>(null)
const selector = ref<HTMLInputElement | null>(null)
const portada = ref<File | null>(null)
const selectorPortada = ref<HTMLInputElement | null>(null)
const enviando = ref(false)
const errorServidor = ref('')
const arrastrando = ref(false)
const errores = reactive({ titulo: '', artista: '', album: '', archivo: '', portada: '' })

function errorDeArchivo(file: File | null): string {
  if (!file) return 'Elige un archivo MP3, OGG o WAV.'
  const nombre = file.name.toLowerCase()
  if (!EXTENSIONES.some((ext) => nombre.endsWith(ext))) return MENSAJES_API.unsupported_format
  if (file.size > MAX_BYTES) return MENSAJES_API.file_too_large
  return ''
}

function elegir(file: File | null): void {
  archivo.value = file
  errores.archivo = file ? errorDeArchivo(file) : ''
}

function errorDePortada(file: File | null): string {
  if (!file) return ''
  if (file.type && !TIPOS_PORTADA.includes(file.type)) return 'La portada debe ser PNG, JPG o WebP.'
  if (file.size > PORTADA_MAX_BYTES) return 'La portada debe pesar 2 MB o menos.'
  return ''
}

function onPortada(): void {
  portada.value = selectorPortada.value?.files?.[0] ?? null
  errores.portada = errorDePortada(portada.value)
}

function onSelector(): void {
  elegir(selector.value?.files?.[0] ?? null)
}

function onSoltar(evento: DragEvent): void {
  arrastrando.value = false
  elegir(evento.dataTransfer?.files?.[0] ?? null)
}

function validar(): boolean {
  errores.titulo = titulo.value.trim() ? '' : 'Escribe el título.'
  errores.artista = artista.value.trim() ? '' : 'Escribe el artista.'
  errores.album = album.value.trim() ? '' : 'Escribe el álbum.'
  errores.archivo = errorDeArchivo(archivo.value)
  errores.portada = errorDePortada(portada.value)
  errorServidor.value = ''
  return !errores.titulo && !errores.artista && !errores.album && !errores.archivo && !errores.portada
}

function limpiar(): void {
  titulo.value = ''
  artista.value = ''
  album.value = ''
  archivo.value = null
  portada.value = null
  if (selector.value) selector.value.value = ''
  if (selectorPortada.value) selectorPortada.value.value = ''
}

async function enviar(): Promise<void> {
  if (enviando.value || !validar() || !archivo.value) return
  const form = new FormData()
  form.append('title', titulo.value.trim())
  form.append('artist', artista.value.trim())
  form.append('album', album.value.trim())
  form.append('file', archivo.value)

  const imagen = portada.value
  enviando.value = true
  try {
    let cancion = await songs.upload(form)
    limpiar()
    // La canción ya existe: si la portada falla no se deshace, se avisa para reintentar.
    if (imagen) {
      try {
        cancion = await songs.uploadCover(cancion.id, imagen)
        mostrar('Canción subida con portada')
      } catch {
        mostrar('La canción se subió, pero la portada no. Inténtalo desde la tabla.', 'error')
      }
    } else {
      mostrar('Canción subida')
    }
    emit('subida', cancion)
  } catch (e) {
    errorServidor.value =
      e instanceof ApiError
        ? (MENSAJES_API[e.code] ?? e.message)
        : 'Algo salió mal. Vuelve a intentarlo.'
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <section class="subida" aria-labelledby="titulo-subida">
    <h2 id="titulo-subida">Subir canción</h2>

    <AvisoEnLinea v-if="errorServidor">{{ errorServidor }}</AvisoEnLinea>

    <form class="subida__form" novalidate @submit.prevent="enviar">
      <div class="campo">
        <label for="subida-titulo">Título</label>
        <input
          id="subida-titulo"
          v-model="titulo"
          type="text"
          maxlength="200"
          :class="{ 'campo--error': errores.titulo }"
          :aria-invalid="!!errores.titulo"
          :aria-describedby="errores.titulo ? 'error-subida-titulo' : undefined"
        />
        <p v-if="errores.titulo" id="error-subida-titulo" class="campo__error">{{ errores.titulo }}</p>
      </div>

      <div class="campo">
        <label for="subida-artista">Artista</label>
        <input
          id="subida-artista"
          v-model="artista"
          type="text"
          maxlength="200"
          :class="{ 'campo--error': errores.artista }"
          :aria-invalid="!!errores.artista"
          :aria-describedby="errores.artista ? 'error-subida-artista' : undefined"
        />
        <p v-if="errores.artista" id="error-subida-artista" class="campo__error">{{ errores.artista }}</p>
      </div>

      <div class="campo">
        <label for="subida-album">Álbum</label>
        <input
          id="subida-album"
          v-model="album"
          type="text"
          maxlength="200"
          :class="{ 'campo--error': errores.album }"
          :aria-invalid="!!errores.album"
          :aria-describedby="errores.album ? 'error-subida-album' : undefined"
        />
        <p v-if="errores.album" id="error-subida-album" class="campo__error">{{ errores.album }}</p>
      </div>

      <div class="campo">
        <label for="subida-archivo">Archivo</label>
        <div
          class="subida__zona"
          :class="{ 'subida__zona--activa': arrastrando }"
          @dragover.prevent="arrastrando = true"
          @dragleave="arrastrando = false"
          @drop.prevent="onSoltar"
        >
          <input
            id="subida-archivo"
            ref="selector"
            type="file"
            accept=".mp3,.ogg,.wav"
            :aria-invalid="!!errores.archivo"
            :aria-describedby="errores.archivo ? 'error-subida-archivo' : 'ayuda-subida-archivo'"
            @change="onSelector"
          />
          <p id="ayuda-subida-archivo" class="subida__ayuda">
            {{ archivo ? archivo.name : 'Arrastra un archivo aquí o elígelo. MP3, OGG o WAV, hasta 20 MB.' }}
          </p>
        </div>
        <p v-if="errores.archivo" id="error-subida-archivo" class="campo__error">{{ errores.archivo }}</p>
      </div>

      <div class="campo">
        <label for="subida-portada">Portada <span class="subida__opcional">(opcional)</span></label>
        <input
          id="subida-portada"
          ref="selectorPortada"
          type="file"
          accept="image/png,image/jpeg,image/webp"
          :aria-invalid="!!errores.portada"
          :aria-describedby="errores.portada ? 'error-subida-portada' : 'ayuda-subida-portada'"
          @change="onPortada"
        />
        <p v-if="errores.portada" id="error-subida-portada" class="campo__error">{{ errores.portada }}</p>
        <p v-else id="ayuda-subida-portada" class="campo__ayuda">PNG, JPG o WebP, hasta 2 MB.</p>
      </div>

      <button type="submit" class="boton-principal" :disabled="enviando" :aria-busy="enviando || undefined">
        {{ enviando ? 'Subiendo…' : 'Subir canción' }}
      </button>
    </form>
  </section>
</template>

<style scoped>
.subida {
  display: grid;
  gap: var(--space-4);
}

.subida__form {
  display: grid;
  gap: var(--space-4);
}

/* El error va sobre --bg, donde --danger cumple contraste. */
.subida .campo__error {
  justify-self: start;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-s);
  background: var(--bg);
}

.subida__zona {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-4);
  border: 2px dashed var(--ink);
  border-radius: var(--radius-m);
}

.subida__zona--activa {
  background: color-mix(in srgb, var(--ink) 12%, transparent);
}

.subida__zona input {
  max-width: 100%;
  min-height: 40px;
}

.subida__ayuda {
  margin: 0;
  font-size: 13px;
  overflow-wrap: anywhere;
}
</style>
