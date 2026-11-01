import { request } from './http'
import type { SongOut, SongPage, SongUpdate } from './types'

export function list(q?: string, offset = 0) {
  const params = new URLSearchParams()
  if (q) params.set('q', q)
  if (offset) params.set('offset', String(offset))
  const query = params.toString()
  return request<SongPage>(`/api/songs${query ? `?${query}` : ''}`)
}

export const streamUrl = (id: string): string => `/api/songs/${id}/stream`

// Sin Content-Type: el navegador lo fija con el boundary del multipart.
export const upload = (form: FormData) =>
  request<SongOut>('/api/songs', { method: 'POST', body: form })

export const update = (id: string, data: SongUpdate) =>
  request<SongOut>(`/api/songs/${id}`, { method: 'PATCH', json: data })

export const deactivate = (id: string) => request<void>(`/api/songs/${id}`, { method: 'DELETE' })

export const coverUrl = (id: string): string => `/api/songs/${id}/cover`

export function uploadCover(id: string, file: File) {
  const form = new FormData()
  form.append('file', file)
  return request<SongOut>(`/api/songs/${id}/cover`, { method: 'PUT', body: form })
}
