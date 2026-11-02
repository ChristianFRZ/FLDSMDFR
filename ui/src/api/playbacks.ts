import { request } from './http'
import type { PlaybackIn, PlaybackOut } from './types'

export const send = (body: PlaybackIn) =>
  request<PlaybackOut>('/api/playbacks', { method: 'POST', json: body })
