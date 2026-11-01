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
  has_cover: boolean
  created_at?: string | null
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

export type PlaylistRole = 'owner' | 'collaborator'

export interface PlaylistSummary {
  id: string
  name: string
  song_count: number
  updated_at: string
  has_cover: boolean
  role: PlaylistRole
}

export interface MemberOut {
  user_id: string
  name: string
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
  has_cover: boolean
  role: PlaylistRole
  members: MemberOut[]
}

export interface InviteOut {
  token: string
  url: string
}

export interface ClaimOut {
  playlist_id: string
  playlist_name: string
  status: 'pending' | 'accepted' | 'ignored' | 'member'
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
  song?: SongOut | null
}

export interface MetricsSummary {
  total_playbacks: number
  total_songs: number
  total_users: number
  top: TopSongOut[]
}

export interface HistoryItemOut {
  song: SongOut
  last_played_at: string
  available: boolean
}

export interface HistoryPage {
  items: HistoryItemOut[]
  total: number
}

export interface TopArtistOut {
  artist: string
  play_count: number
  song_count: number
  cover_song_id: string | null
}

export interface FavoriteSongOut {
  song_id: string
  title: string
  artist: string
  album: string
  duration_seconds: number
  has_cover: boolean
  status: 'ok' | 'unavailable'
  added_at: string
}

export interface FavoritesOut {
  songs: FavoriteSongOut[]
  total_seconds: number
}

export interface FollowOut {
  artist: string
  followed_at: string
  song_count: number
  cover_song_id: string | null
}

export interface InviteNotice {
  token: string
  playlist_id: string
  playlist_name: string
  inviter_name: string
}

export interface NotificationOut {
  id: string
  type: 'release' | 'invite'
  created_at: string
  read: boolean
  song: SongOut | null
  invite: InviteNotice | null
}

export interface NotificationsOut {
  items: NotificationOut[]
  unread_count: number
}
