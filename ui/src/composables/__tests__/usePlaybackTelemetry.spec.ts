import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPlaybackTelemetry } from '../usePlaybackTelemetry'
import type { PlaybackIn } from '../../api/types'

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

  it('ignores ticks without a session', () => {
    const { telemetry, sendMock } = setup()
    tick(telemetry, 0, 12)
    expect(sendMock).not.toHaveBeenCalled()
  })
})
