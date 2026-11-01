import { request } from './http'
import type { FavoritesOut, FollowOut, HistoryPage, NotificationsOut } from './types'

export const history = (limit = 20, offset = 0) =>
  request<HistoryPage>(`/api/me/history?limit=${limit}&offset=${offset}`)

export const favorites = () => request<FavoritesOut>('/api/me/favorites')

export const favoriteIds = () => request<string[]>('/api/me/favorites/ids')

export const like = (songId: string) =>
  request<void>(`/api/me/favorites/${songId}`, { method: 'PUT' })

export const unlike = (songId: string) =>
  request<void>(`/api/me/favorites/${songId}`, { method: 'DELETE' })

export const follows = () => request<FollowOut[]>('/api/me/follows')

const followPath = (artist: string) => `/api/me/follows/${encodeURIComponent(artist)}`

export const follow = (artist: string) => request<void>(followPath(artist), { method: 'PUT' })

export const unfollow = (artist: string) => request<void>(followPath(artist), { method: 'DELETE' })

export const notifications = () => request<NotificationsOut>('/api/me/notifications')

export const markRead = (ids: string[]) =>
  request<void>('/api/me/notifications/read', { method: 'POST', json: { ids } })
