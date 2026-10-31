import { ref, watch } from 'vue'
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
    ['ended', next],
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

async function play(song: SongOut, newQueue?: SongOut[]): Promise<void> {
  if (!audio) return
  current.value = song
  queue.value = newQueue ?? [song]
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
  return queue.value.findIndex((song) => song.id === id)
}

function next(): void {
  const index = indexOfCurrent()
  const following = index >= 0 ? queue.value[index + 1] : undefined
  if (following) void play(following, queue.value)
  else isPlaying.value = false
}

function prev(): void {
  const index = indexOfCurrent()
  const previous = index > 0 ? queue.value[index - 1] : undefined
  if (currentTime.value > REINICIO_SEGUNDOS || !previous) seek(0)
  else void play(previous, queue.value)
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
    attach,
    play,
    toggle,
    next,
    prev,
    seek,
    stop,
    setVolume,
  }
}
