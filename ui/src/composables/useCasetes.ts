import { ref, type Ref } from 'vue'
import { ApiError } from '../api/http'
import * as playlists from '../api/playlists'
import type { PlaylistDetail, PlaylistSummary } from '../api/types'
import { useAvisos } from './useAvisos'

// Estado singleton: la biblioteca, el selector para grabar y las vistas comparten la lista.
const casetes = ref<PlaylistSummary[]>([])
const cargando = ref(false)
const error = ref('')

const CLAVE_ULTIMO = 'meloxo.ultimoCasete'

function leerUltimo(): string | null {
  try {
    return localStorage.getItem(CLAVE_ULTIMO)
  } catch {
    return null
  }
}

function guardarUltimo(id: string | null): void {
  try {
    if (id) localStorage.setItem(CLAVE_ULTIMO, id)
    else localStorage.removeItem(CLAVE_ULTIMO)
  } catch {
    // Sin almacenamiento solo se pierde la preferencia.
  }
}

/** Último casete donde se grabó: aparece primero en el selector. */
const ultimoDestino = ref<string | null>(leerUltimo())

// Cambia al reiniciar (cerrar sesión): descarta listas que lleguen de la sesión anterior.
let generacion = 0

const { mostrar } = useAvisos()

function mensajeDe(e: unknown): string {
  return e instanceof ApiError ? e.message : 'Algo salió mal. Vuelve a intentarlo.'
}

async function cargar(): Promise<void> {
  const miGeneracion = generacion
  cargando.value = true
  error.value = ''
  try {
    const lista = await playlists.list()
    if (miGeneracion === generacion) casetes.value = lista
  } catch (e) {
    if (miGeneracion === generacion) error.value = mensajeDe(e)
  } finally {
    if (miGeneracion === generacion) cargando.value = false
  }
}

/** Crea un casete. Propaga el error para mostrarlo junto al campo. */
async function crear(nombre: string): Promise<PlaylistSummary> {
  const nuevo = await playlists.create(nombre)
  casetes.value = [nuevo, ...casetes.value.filter((c) => c.id !== nuevo.id)]
  return nuevo
}

/** Refleja en la lista el nombre, conteo y portada de un detalle recibido. */
function sincronizar(detalle: PlaylistDetail): void {
  casetes.value = casetes.value.map((c) =>
    c.id === detalle.id
      ? { ...c, name: detalle.name, song_count: detalle.songs.length, has_cover: detalle.has_cover }
      : c,
  )
}

/** Quita un casete de la lista (borrado o acceso perdido). */
function olvidar(id: string): void {
  casetes.value = casetes.value.filter((c) => c.id !== id)
  if (ultimoDestino.value === id) {
    ultimoDestino.value = null
    guardarUltimo(null)
  }
}

/** Graba una canción en un casete. Devuelve si quedó grabada; los errores se avisan aquí. */
async function grabar(caseteId: string, songId: string): Promise<boolean> {
  const nombre = casetes.value.find((c) => c.id === caseteId)?.name ?? 'el casete'
  try {
    sincronizar(await playlists.addSong(caseteId, songId))
  } catch (e) {
    if (e instanceof ApiError && e.code === 'song_already_in_playlist') {
      mostrar(`Esa canción ya está en «${nombre}».`, 'info')
    } else {
      mostrar(mensajeDe(e), 'error')
    }
    return false
  }
  ultimoDestino.value = caseteId
  guardarUltimo(caseteId)
  mostrar(`Grabada en «${nombre}»`, 'info')
  return true
}

/** Vacía el estado (al cerrar sesión) para que el siguiente usuario no vea casetes ajenos. */
function reiniciar(): void {
  generacion++
  casetes.value = []
  cargando.value = false
  error.value = ''
  ultimoDestino.value = null
  guardarUltimo(null)
}

export function useCasetes(): {
  casetes: Ref<PlaylistSummary[]>
  cargando: Ref<boolean>
  error: Ref<string>
  ultimoDestino: Ref<string | null>
  cargar: () => Promise<void>
  crear: (nombre: string) => Promise<PlaylistSummary>
  grabar: (caseteId: string, songId: string) => Promise<boolean>
  sincronizar: (detalle: PlaylistDetail) => void
  olvidar: (id: string) => void
  reiniciar: () => void
} {
  return { casetes, cargando, error, ultimoDestino, cargar, crear, grabar, sincronizar, olvidar, reiniciar }
}
