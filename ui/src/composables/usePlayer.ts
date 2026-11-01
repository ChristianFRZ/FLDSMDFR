import { computed, ref, watch } from 'vue'
import * as playbacks from '../api/playbacks'
import * as songs from '../api/songs'
import type { SongOut } from '../api/types'
import { useAvisos } from './useAvisos'
import { createPlaybackTelemetry } from './usePlaybackTelemetry'

/** Pasado este punto, "anterior" reinicia la canción en vez de saltar a la previa. */
const REINICIO_SEGUNDOS = 3

// Estado singleton a nivel de módulo: el reproductor se comparte entre vistas.
const current = ref<SongOut | null>(null)
const queue = ref<SongOut[]>([])
const isPlaying = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const buffered = ref<Array<[number, number]>>([])
const volume = ref(1)

export type ModoRepetir = 'off' | 'all' | 'one'
const CLAVE_ALEATORIO = 'meloxo.shuffle'
const CLAVE_REPETIR = 'meloxo.repeat'

function leer(clave: string): string | null {
  try {
    return localStorage.getItem(clave)
  } catch {
    return null
  }
}

function guardar(clave: string, valor: string): void {
  try {
    localStorage.setItem(clave, valor)
  } catch {
    // Almacenamiento bloqueado (modo privado): la preferencia dura solo esta sesión.
  }
}

const repetirGuardado = leer(CLAVE_REPETIR)
const shuffle = ref(leer(CLAVE_ALEATORIO) === '1')
const repeat = ref<ModoRepetir>(
  repetirGuardado === 'all' || repetirGuardado === 'one' ? repetirGuardado : 'off',
)
// Orden real de reproducción: igual a `queue` o una permutación de ella si hay aleatorio.
const orden = ref<SongOut[]>([])

const telemetry = createPlaybackTelemetry({ send: playbacks.send })
const { mostrar } = useAvisos()

watch(telemetry.status, (status) => {
  if (status === 'failed') {
    mostrar('No pudimos registrar esta reproducción; la música sigue.', 'info')
  }
})

let audio: HTMLAudioElement | null = null
let detach: (() => void) | null = null

function readBuffered(el: HTMLAudioElement): Array<[number, number]> {
  const ranges: Array<[number, number]> = []
  const timeRanges = el.buffered
  for (let i = 0; i < (timeRanges?.length ?? 0); i++) {
    ranges.push([timeRanges.start(i), timeRanges.end(i)])
  }
  return ranges
}

function fallarReproduccion(): void {
  isPlaying.value = false
  mostrar('No se pudo reproducir la canción.', 'error')
}

function attach(el: HTMLAudioElement): void {
  detach?.()
  audio = el
  el.volume = volume.value

  const onTimeUpdate = () => {
    currentTime.value = el.currentTime
    buffered.value = readBuffered(el)
    telemetry.onTimeUpdate(el.currentTime)
  }
  const onProgress = () => {
    buffered.value = readBuffered(el)
  }
  const onDuration = () => {
    duration.value = Number.isFinite(el.duration) ? el.duration : 0
  }
  const onPlay = () => {
    isPlaying.value = true
  }
  const onPause = () => {
    isPlaying.value = false
  }
  const handlers: Array<[string, () => void]> = [
    ['timeupdate', onTimeUpdate],
    ['progress', onProgress],
    ['durationchange', onDuration],
    ['loadedmetadata', onDuration],
    ['play', onPlay],
    ['pause', onPause],
    ['ended', alTerminar],
    ['error', fallarReproduccion],
  ]
  for (const [name, handler] of handlers) el.addEventListener(name, handler)
  detach = () => {
    for (const [name, handler] of handlers) el.removeEventListener(name, handler)
    if (audio === el) audio = null
  }
}

/** La telemetría nunca debe impedir que suene la música: si falla, se avisa y se sigue. */
function iniciarSesionDeEscucha(songId: string): void {
  try {
    telemetry.startSession(songId)
  } catch {
    mostrar('No pudimos registrar esta reproducción; la música sigue.', 'info')
  }
}

/** Fisher–Yates: la canción elegida va primero y el resto se baraja una sola vez. */
function barajar(primera: SongOut | null, canciones: SongOut[]): SongOut[] {
  const resto = canciones.filter((s) => s.id !== primera?.id)
  for (let i = resto.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[resto[i], resto[j]] = [resto[j], resto[i]]
  }
  return primera ? [primera, ...resto] : resto
}

function rehacerOrden(): void {
  orden.value = shuffle.value ? barajar(current.value, queue.value) : [...queue.value]
}

async function play(song: SongOut, newQueue?: SongOut[]): Promise<void> {
  if (!audio) return
  const cambiaCola = newQueue !== undefined || !queue.value.some((s) => s.id === song.id)
  current.value = song
  if (cambiaCola) {
    queue.value = newQueue ?? [song]
    rehacerOrden()
  }
  currentTime.value = 0
  duration.value = song.duration_seconds
  buffered.value = []
  audio.src = songs.streamUrl(song.id)
  iniciarSesionDeEscucha(song.id)
  try {
    await audio.play()
    isPlaying.value = true
  } catch (error) {
    // Un play() interrumpido por otra carga (cambio rápido de canción) no es un fallo.
    if (error instanceof DOMException && error.name === 'AbortError') return
    // Si el medio falló al cargar, el evento `error` ya avisó: no se avisa dos veces.
    if (audio?.error) return
    fallarReproduccion()
  }
}

function toggle(): void {
  if (!audio || !current.value) return
  if (audio.paused) {
    // Repetir desde el principio tras terminar es una escucha nueva (spec §4.8).
    if (audio.ended) iniciarSesionDeEscucha(current.value.id)
    audio.play().catch((error) => {
      const abortado = error instanceof DOMException && error.name === 'AbortError'
      if (!abortado && !audio?.error) fallarReproduccion()
    })
  } else {
    audio.pause()
  }
}

function indexOfCurrent(): number {
  const id = current.value?.id
  return orden.value.findIndex((song) => song.id === id)
}

function next(): void {
  const index = indexOfCurrent()
  let following = index >= 0 ? orden.value[index + 1] : undefined
  if (!following && repeat.value === 'all' && orden.value.length > 1) following = orden.value[0]
  if (following) void play(following)
  else isPlaying.value = false
}

function prev(): void {
  const index = indexOfCurrent()
  const previous = index > 0 ? orden.value[index - 1] : undefined
  if (currentTime.value > REINICIO_SEGUNDOS || !previous) seek(0)
  else void play(previous)
}

/** Fin de la canción: con "repetir una" vuelve a empezar como escucha nueva. */
function alTerminar(): void {
  if (repeat.value === 'one' && audio && current.value) {
    seek(0)
    iniciarSesionDeEscucha(current.value.id)
    audio.play().catch(() => fallarReproduccion())
    return
  }
  next()
}

function toggleShuffle(): void {
  shuffle.value = !shuffle.value
  guardar(CLAVE_ALEATORIO, shuffle.value ? '1' : '0')
  rehacerOrden()
}

function cycleRepeat(): void {
  const siguiente: Record<ModoRepetir, ModoRepetir> = { off: 'all', all: 'one', one: 'off' }
  repeat.value = siguiente[repeat.value]
  guardar(CLAVE_REPETIR, repeat.value)
}

/** Lo que sigue tras la canción actual, en el orden real de reproducción. */
const upcoming = computed(() => orden.value.slice(indexOfCurrent() + 1))

function editarLoQueSigue(editar: (siguientes: SongOut[]) => SongOut[]): void {
  const corte = indexOfCurrent() + 1
  orden.value = [...orden.value.slice(0, corte), ...editar(orden.value.slice(corte))]
  if (!shuffle.value) queue.value = [...orden.value]
}

function enqueue(song: SongOut): void {
  if (!current.value) {
    void play(song, [song])
    return
  }
  if (shuffle.value) queue.value = [...queue.value, song]
  editarLoQueSigue((siguientes) => [...siguientes.filter((s) => s.id !== song.id), song])
}

function playNext(song: SongOut): void {
  if (!current.value) {
    void play(song, [song])
    return
  }
  if (shuffle.value) queue.value = [...queue.value, song]
  editarLoQueSigue((siguientes) => [song, ...siguientes.filter((s) => s.id !== song.id)])
}

function removeFromQueue(index: number): void {
  const quitada = upcoming.value[index]
  if (!quitada) return
  queue.value = queue.value.filter((s) => s.id !== quitada.id)
  editarLoQueSigue((siguientes) => siguientes.filter((_, i) => i !== index))
}

function moveInQueue(from: number, to: number): void {
  editarLoQueSigue((siguientes) => {
    if (from < 0 || from >= siguientes.length || to < 0 || to >= siguientes.length) return siguientes
    const copia = [...siguientes]
    const [movida] = copia.splice(from, 1)
    copia.splice(to, 0, movida)
    return copia
  })
}

function seek(seconds: number): void {
  if (!audio) return
  const max = duration.value > 0 ? duration.value : seconds
  const target = Math.min(Math.max(seconds, 0), max)
  audio.currentTime = target
  currentTime.value = target
}

/** Detiene y vacía el reproductor (p. ej. al cerrar sesión): sin canción, sin cola, sin fuente. */
function stop(): void {
  if (audio) {
    audio.pause()
    // Quitar el atributo (no asignar '') evita un evento `error` y su aviso.
    audio.removeAttribute('src')
    audio.load()
  }
  current.value = null
  queue.value = []
  orden.value = []
  isPlaying.value = false
  currentTime.value = 0
  duration.value = 0
  buffered.value = []
}

function setVolume(v: number): void {
  const clamped = Math.min(Math.max(Number.isFinite(v) ? v : 0, 0), 1)
  volume.value = clamped
  if (audio) audio.volume = clamped
}

export function usePlayer() {
  return {
    current,
    queue,
    isPlaying,
    currentTime,
    duration,
    buffered,
    volume,
    shuffle,
    repeat,
    upcoming,
    attach,
    play,
    toggle,
    next,
    prev,
    seek,
    stop,
    setVolume,
    toggleShuffle,
    cycleRepeat,
    enqueue,
    playNext,
    removeFromQueue,
    moveInQueue,
  }
}
