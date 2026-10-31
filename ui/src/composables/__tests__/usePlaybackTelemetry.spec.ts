import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPlaybackTelemetry } from '../usePlaybackTelemetry'
import type { PlaybackIn } from '../../api/types'
import { ApiError } from '../../api/http'

function setup(send: (b: PlaybackIn) => Promise<unknown> = () => Promise.resolve({})) {
  const sendMock = vi.fn(send)
  const delays: number[] = []
  const sleep = (ms: number) => {
    delays.push(ms)
    return new Promise<void>((resolve) => setTimeout(resolve, ms))
  }
  let n = 0
  const uuid = () => `id-${++n}`
  const telemetry = createPlaybackTelemetry({ send: sendMock, sleep, uuid })
  return { telemetry, sendMock, delays }
}

/** Avanza el reloj de reproducción de `from` a `to` en pasos de 0.25 s. */
function tick(t: ReturnType<typeof createPlaybackTelemetry>, from: number, to: number) {
  for (let x = from; x <= to + 1e-9; x += 0.25) t.onTimeUpdate(x)
}

describe('createPlaybackTelemetry', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('sends once after 10 listened seconds', async () => {
    const { telemetry, sendMock } = setup()
    telemetry.startSession('song-1')
    tick(telemetry, 0, 12)
    await vi.advanceTimersByTimeAsync(0)
    expect(sendMock).toHaveBeenCalledTimes(1)
    expect(sendMock).toHaveBeenCalledWith({
      playback_id: 'id-1',
      song_id: 'song-1',
      listened_seconds: 10,
    })
    expect(telemetry.status.value).toBe('sent')
  })

  it('does not send before 10 seconds', async () => {
    const { telemetry, sendMock } = setup()
    telemetry.startSession('song-1')
    tick(telemetry, 0, 9)
    await vi.advanceTimersByTimeAsync(0)
    expect(sendMock).not.toHaveBeenCalled()
    expect(telemetry.status.value).toBe('counting')
  })

  it('seeks do not count', async () => {
    const { telemetry, sendMock } = setup()
    telemetry.startSession('song-1')
    tick(telemetry, 0, 5)
    telemetry.onTimeUpdate(60)
    tick(telemetry, 60.25, 64)
    await vi.advanceTimersByTimeAsync(0)
    expect(sendMock).not.toHaveBeenCalled()
    tick(telemetry, 64.25, 70)
    await vi.advanceTimersByTimeAsync(0)
    expect(sendMock).toHaveBeenCalledTimes(1)
    expect(sendMock.mock.calls[0][0].listened_seconds).toBe(10)
  })

  it('backward jumps do not count', async () => {
    const { telemetry, sendMock } = setup()
    telemetry.startSession('song-1')
    tick(telemetry, 0, 7)
    telemetry.onTimeUpdate(1)
    tick(telemetry, 1.25, 3)
    await vi.advanceTimersByTimeAsync(0)
    expect(sendMock).not.toHaveBeenCalled()
  })

  it('retries with same playback_id', async () => {
    let calls = 0
    const { telemetry, sendMock, delays } = setup(() =>
      ++calls <= 2 ? Promise.reject(new Error('red')) : Promise.resolve({}),
    )
    telemetry.startSession('song-1')
    tick(telemetry, 0, 10)
    await vi.advanceTimersByTimeAsync(0)
    expect(telemetry.status.value).toBe('sending')
    await vi.advanceTimersByTimeAsync(1000)
    await vi.advanceTimersByTimeAsync(2000)
    expect(sendMock).toHaveBeenCalledTimes(3)
    const ids = sendMock.mock.calls.map((c) => c[0].playback_id)
    expect(new Set(ids).size).toBe(1)
    expect(delays).toEqual([1000, 2000])
    expect(telemetry.status.value).toBe('sent')
  })

  it('gives up after 4 attempts', async () => {
    const { telemetry, sendMock, delays } = setup(() => Promise.reject(new Error('red')))
    telemetry.startSession('song-1')
    tick(telemetry, 0, 10)
    await vi.advanceTimersByTimeAsync(10_000)
    expect(sendMock).toHaveBeenCalledTimes(4)
    expect(delays).toEqual([1000, 2000, 4000])
    expect(telemetry.status.value).toBe('failed')
  })

  it('new session gets new id', async () => {
    const { telemetry, sendMock } = setup()
    telemetry.startSession('song-1')
    tick(telemetry, 0, 10)
    await vi.advanceTimersByTimeAsync(0)
    telemetry.startSession('song-2')
    expect(telemetry.status.value).toBe('counting')
    tick(telemetry, 0, 10)
    await vi.advanceTimersByTimeAsync(0)
    expect(sendMock).toHaveBeenCalledTimes(2)
    expect(sendMock.mock.calls[0][0].playback_id).toBe('id-1')
    expect(sendMock.mock.calls[1][0].playback_id).toBe('id-2')
    expect(sendMock.mock.calls[1][0].song_id).toBe('song-2')
  })

  it('stale session retries never touch the status of the current session', async () => {
    const { telemetry, sendMock } = setup(() => Promise.reject(new Error('red')))
    telemetry.startSession('song-1')
    tick(telemetry, 0, 10)
    await vi.advanceTimersByTimeAsync(0)
    expect(telemetry.status.value).toBe('sending')
    telemetry.startSession('song-2')
    tick(telemetry, 0, 5)
    await vi.advanceTimersByTimeAsync(10_000)
    // La sesión 1 agotó sus 4 intentos, pero la 2 sigue contando.
    expect(sendMock).toHaveBeenCalledTimes(4)
    expect(sendMock.mock.calls.every((c) => c[0].playback_id === 'id-1')).toBe(true)
    expect(telemetry.status.value).toBe('counting')
  })

  it('ignores ticks without a session', () => {
    const { telemetry, sendMock } = setup()
    tick(telemetry, 0, 12)
    expect(sendMock).not.toHaveBeenCalled()
  })

  it('genera un UUID v4 válido sin crypto.randomUUID', async () => {
    vi.stubGlobal('crypto', { getRandomValues: (a: Uint8Array) => a.fill(255) })
    try {
      const sendMock = vi.fn((_: PlaybackIn) => Promise.resolve({}))
      const telemetry = createPlaybackTelemetry({ send: sendMock })
      telemetry.startSession('song-1')
      tick(telemetry, 0, 10)
      await vi.advanceTimersByTimeAsync(0)
      expect(sendMock.mock.calls[0][0].playback_id).toMatch(
        /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
      )
    } finally {
      vi.unstubAllGlobals()
    }
  })

  it('no reintenta errores 4xx: falla de inmediato', async () => {
    const { telemetry, sendMock, delays } = setup(() =>
      Promise.reject(new ApiError(422, 'invalid_input', 'Datos inválidos')),
    )
    telemetry.startSession('song-1')
    tick(telemetry, 0, 10)
    await vi.advanceTimersByTimeAsync(0)
    expect(sendMock).toHaveBeenCalledTimes(1)
    expect(delays).toEqual([])
    expect(telemetry.status.value).toBe('failed')
  })

  it('reintenta errores de red y 5xx', async () => {
    for (const error of [
      new ApiError(0, 'network_error', 'Sin conexión'),
      new ApiError(503, 'unavailable', 'Caído'),
    ]) {
      let calls = 0
      const { telemetry, sendMock } = setup(() =>
        ++calls === 1 ? Promise.reject(error) : Promise.resolve({}),
      )
      telemetry.startSession('song-1')
      tick(telemetry, 0, 10)
      await vi.advanceTimersByTimeAsync(1000)
      expect(sendMock).toHaveBeenCalledTimes(2)
      expect(telemetry.status.value).toBe('sent')
    }
  })
})
