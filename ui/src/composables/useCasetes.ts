import { ref, type Ref } from 'vue'
import { ApiError } from '../api/http'
import * as playlists from '../api/playlists'
import type { PlaylistDetail, PlaylistSummary } from '../api/types'
import { useAvisos } from './useAvisos'

// Estado singleton a nivel de módulo: la casetera y sus paneles comparten los casetes.
const casetes = ref<PlaylistSummary[]>([])
const activo = ref<PlaylistDetail | null>(null)
const cargando = ref(false)
const error = ref('')

// Cada selección incrementa el turno; una respuesta de un turno viejo se descarta.
let turno = 0

const { mostrar } = useAvisos()

function mensajeDe(e: unknown): string {
  return e instanceof ApiError ? e.message : 'Algo salió mal. Vuelve a intentarlo.'
}

/** Refleja en el resumen del estante el conteo y nombre del detalle recibido. */
function sincronizarResumen(detalle: PlaylistDetail): void {
  casetes.value = casetes.value.map((c) =>
    c.id === detalle.id ? { ...c, name: detalle.name, song_count: detalle.songs.length } : c,
  )
}

function aplicarDetalle(detalle: PlaylistDetail): void {
  activo.value = detalle
  sincronizarResumen(detalle)
}

async function seleccionar(id: string): Promise<void> {
  const miTurno = ++turno
  cargando.value = true
  error.value = ''
  try {
    const detalle = await playlists.get(id)
    if (miTurno === turno) aplicarDetalle(detalle)
  } catch (e) {
    if (miTurno === turno) error.value = mensajeDe(e)
  } finally {
    if (miTurno === turno) cargando.value = false
  }
}

async function cargar(): Promise<void> {
  cargando.value = true
  error.value = ''
  try {
    casetes.value = await playlists.list()
  } catch (e) {
    error.value = mensajeDe(e)
    cargando.value = false
    return
  }
  // Se conserva el activo si sigue existiendo (p. ej. al volver de la cabina); si no, el primero.
  const sigue = activo.value && casetes.value.some((c) => c.id === activo.value?.id)
  const destino = sigue ? activo.value!.id : casetes.value[0]?.id
  if (destino) {
    await seleccionar(destino)
  } else {
    activo.value = null
    cargando.value = false
  }
}

/** Crea un casete y lo pone en la casetera. Propaga el error para mostrarlo junto al campo. */
async function crear(nombre: string): Promise<void> {
  const nuevo = await playlists.create(nombre)
  casetes.value = [...casetes.value, nuevo]
  mostrar('Casete creado', 'info')
  await seleccionar(nuevo.id)
}

/** Renombra el casete activo. Propaga el error para mostrarlo junto al campo. */
async function renombrar(nombre: string): Promise<void> {
  const actual = activo.value
  if (!actual) return
  const resumen = await playlists.rename(actual.id, nombre)
  casetes.value = casetes.value.map((c) => (c.id === resumen.id ? resumen : c))
  if (activo.value?.id === resumen.id) activo.value = { ...activo.value, name: resumen.name }
}

async function eliminar(): Promise<void> {
  const actual = activo.value
  if (!actual) return
  try {
    await playlists.remove(actual.id)
  } catch (e) {
    mostrar(mensajeDe(e), 'error')
    return
  }
  casetes.value = casetes.value.filter((c) => c.id !== actual.id)
  activo.value = null
  mostrar(`Borraste «${actual.name}»`, 'info')
  const siguiente = casetes.value[0]
  if (siguiente) await seleccionar(siguiente.id)
}

async function grabar(songId: string): Promise<void> {
  const actual = activo.value
  if (!actual) {
    mostrar('Crea un casete primero.', 'error')
    return
  }
  try {
    aplicarDetalle(await playlists.addSong(actual.id, songId))
    mostrar(`Grabada en «${actual.name}»`, 'info')
  } catch (e) {
    if (e instanceof ApiError && e.code === 'song_already_in_playlist') {
      mostrar('Esa canción ya está en este casete.', 'info')
    } else {
      mostrar(mensajeDe(e), 'error')
    }
  }
}

async function quitar(songId: string): Promise<void> {
  const actual = activo.value
  if (!actual) return
  try {
    aplicarDetalle(await playlists.removeSong(actual.id, songId))
  } catch (e) {
    mostrar(mensajeDe(e), 'error')
  }
}

async function mover(songId: string, direccion: -1 | 1): Promise<void> {
  const actual = activo.value
  if (!actual) return
  const ids = actual.songs.map((s) => s.song_id)
  const desde = ids.indexOf(songId)
  const hacia = desde + direccion
  if (desde < 0 || hacia < 0 || hacia >= ids.length) return
  ;[ids[desde], ids[hacia]] = [ids[hacia], ids[desde]]
  try {
    aplicarDetalle(await playlists.reorder(actual.id, ids))
  } catch (e) {
    mostrar(mensajeDe(e), 'error')
  }
}

export function useCasetes(): {
  casetes: Ref<PlaylistSummary[]>
  activo: Ref<PlaylistDetail | null>
  cargando: Ref<boolean>
  error: Ref<string>
  cargar: () => Promise<void>
  seleccionar: (id: string) => Promise<void>
  crear: (nombre: string) => Promise<void>
  renombrar: (nombre: string) => Promise<void>
  eliminar: () => Promise<void>
  grabar: (songId: string) => Promise<void>
  quitar: (songId: string) => Promise<void>
  mover: (songId: string, direccion: -1 | 1) => Promise<void>
} {
  return {
    casetes,
    activo,
    cargando,
    error,
    cargar,
    seleccionar,
    crear,
    renombrar,
    eliminar,
    grabar,
    quitar,
    mover,
  }
}
