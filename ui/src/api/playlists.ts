import { request } from './http'
import type { InviteOut, PlaylistDetail, PlaylistSummary } from './types'

export const list = () => request<PlaylistSummary[]>('/api/playlists')

export const create = (name: string) =>
  request<PlaylistSummary>('/api/playlists', { method: 'POST', json: { name } })

export const get = (id: string) => request<PlaylistDetail>(`/api/playlists/${id}`)

export const rename = (id: string, name: string) =>
  request<PlaylistSummary>(`/api/playlists/${id}`, { method: 'PATCH', json: { name } })

export const remove = (id: string) => request<void>(`/api/playlists/${id}`, { method: 'DELETE' })

export const addSong = (id: string, songId: string) =>
  request<PlaylistDetail>(`/api/playlists/${id}/songs`, {
    method: 'POST',
    json: { song_id: songId },
  })

export const removeSong = (id: string, songId: string) =>
  request<PlaylistDetail>(`/api/playlists/${id}/songs/${songId}`, { method: 'DELETE' })

export const reorder = (id: string, songIds: string[]) =>
  request<PlaylistDetail>(`/api/playlists/${id}/order`, {
    method: 'PUT',
    json: { song_ids: songIds },
  })

export const coverUrl = (id: string): string => `/api/playlists/${id}/cover`

export function uploadCover(id: string, file: File) {
  const form = new FormData()
  form.append('file', file)
  return request<PlaylistSummary>(`/api/playlists/${id}/cover`, { method: 'PUT', body: form })
}

export const createInvite = (id: string) =>
  request<InviteOut>(`/api/playlists/${id}/invites`, { method: 'POST' })

export const revokeInvite = (id: string) =>
  request<void>(`/api/playlists/${id}/invites`, { method: 'DELETE' })

export const removeMember = (id: string, userId: string) =>
  request<void>(`/api/playlists/${id}/members/${userId}`, { method: 'DELETE' })
