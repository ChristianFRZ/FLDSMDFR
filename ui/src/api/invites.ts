import { request } from './http'
import type { ClaimOut, PlaylistSummary } from './types'

const base = (token: string) => `/api/invites/${encodeURIComponent(token)}`

export const claim = (token: string) => request<ClaimOut>(`${base(token)}/claim`, { method: 'POST' })

export const accept = (token: string) =>
  request<PlaylistSummary>(`${base(token)}/accept`, { method: 'POST' })

export const ignore = (token: string) => request<void>(`${base(token)}/ignore`, { method: 'POST' })
