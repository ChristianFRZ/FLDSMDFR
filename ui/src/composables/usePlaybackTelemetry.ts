import { readonly, ref, type Ref } from 'vue'
import type { PlaybackIn } from '../api/types'

export type TelemetryStatus = 'idle' | 'counting' | 'sending' | 'sent' | 'failed'

export interface TelemetryDeps {
  send: (body: PlaybackIn) => Promise<unknown>
  uuid?: () => string
  sleep?: (ms: number) => Promise<void>
}

/** Segundos escuchados necesarios para que una reproducción cuente. */
const UMBRAL_SEGUNDOS = 10
/** Avance máximo entre dos `timeupdate` para considerarlo escucha continua (saltos no suman). */
const SALTO_MAXIMO = 1.5
/** Esperas antes de cada reintento: 1 intento + 3 reintentos. */
const ESPERAS_REINTENTO_MS = [1000, 2000, 4000]

const sleepPorDefecto = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))

/**
 * Telemetría de reproducción idempotente: acumula segundos realmente escuchados y envía
 * una sola vez al llegar a 10 s. Los reintentos reutilizan el mismo `playback_id`, así el
 * servidor no cuenta dos veces. Nunca lanza.
 */
export function createPlaybackTelemetry(deps: TelemetryDeps): {
  startSession: (songId: string) => void
  onTimeUpdate: (currentTime: number) => void
  status: Readonly<Ref<TelemetryStatus>>
} {
  const uuid = deps.uuid ?? (() => crypto.randomUUID())
  const sleep = deps.sleep ?? sleepPorDefecto
  const status = ref<TelemetryStatus>('idle')

  let sessionToken = 0
  let playbackId = ''
  let songId = ''
  let acumulado = 0
  let ultimo = 0
  let enviado = false

  async function enviar(token: number, body: PlaybackIn): Promise<void> {
    // El estado solo lo toca la sesión vigente; una sesión anterior termina en silencio.
    const vigente = () => token === sessionToken
    for (let intento = 0; intento <= ESPERAS_REINTENTO_MS.length; intento++) {
      try {
        await deps.send(body)
        if (vigente()) status.value = 'sent'
        return
      } catch {
        if (intento === ESPERAS_REINTENTO_MS.length) break
        await sleep(ESPERAS_REINTENTO_MS[intento])
      }
    }
    if (vigente()) status.value = 'failed'
  }

  function startSession(newSongId: string): void {
    sessionToken++
    playbackId = uuid()
    songId = newSongId
    acumulado = 0
    ultimo = 0
    enviado = false
    status.value = 'counting'
  }

  function onTimeUpdate(currentTime: number): void {
    if (status.value === 'idle' || enviado) return
    const delta = currentTime - ultimo
    if (delta > 0 && delta <= SALTO_MAXIMO) acumulado += delta
    ultimo = currentTime
    if (acumulado >= UMBRAL_SEGUNDOS) {
      enviado = true
      status.value = 'sending'
      void enviar(sessionToken, {
        playback_id: playbackId,
        song_id: songId,
        listened_seconds: Math.floor(acumulado),
      })
    }
  }

  return { startSession, onTimeUpdate, status: readonly(status) }
}
