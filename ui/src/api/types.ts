// Espejo de los esquemas Pydantic de la API (app/modules/*/schemas.py).
// Los UUID y las fechas viajan como string en JSON.

export type Role = 'listener' | 'admin'

export interface UserOut {
  id: string
  name: string
  email: string
  role: Role
}

export interface TokenOut {
  access_token: string
  token_type: 'bearer'
  user: UserOut
}

export interface SongOut {
  id: string
  title: string
  artist: string
  album: string
  duration_seconds: number
  is_active: boolean
}

export interface SongPage {
  items: SongOut[]
  total: number
}

export interface SongUpdate {
  title?: string
  artist?: string
  album?: string
}

export interface PlaylistSummary {
  id: string
  name: string
  song_count: number
  updated_at: string
}

export type PlaylistSongStatus = 'ok' | 'degraded' | 'unavailable'

export interface PlaylistSongOut {
  song_id: string
  title: string
  artist: string
  album: string
  duration_seconds: number
  position: number
  status: PlaylistSongStatus
}

export interface PlaylistDetail {
  id: string
  name: string
  songs: PlaylistSongOut[]
  total_seconds: number
}

export interface PlaybackIn {
  playback_id: string
  song_id: string
  listened_seconds: number
  occurred_at?: string | null
}

export interface PlaybackOut {
  playback_id: string
  counted: boolean
}

export interface TopSongOut {
  song_id: string
  title: string
  artist: string
  album: string
  play_count: number
}

export interface MetricsSummary {
  total_playbacks: number
  total_songs: number
  total_users: number
  top: TopSongOut[]
}
