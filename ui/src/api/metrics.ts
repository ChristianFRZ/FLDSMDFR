import { request } from './http'
import type { MetricsSummary, TopArtistOut, TopSongOut } from './types'

export const top = (limit?: number) =>
  request<TopSongOut[]>(`/api/metrics/top${limit ? `?limit=${limit}` : ''}`)

export const summary = () => request<MetricsSummary>('/api/metrics/summary')

export const topArtists = (limit?: number) =>
  request<TopArtistOut[]>(`/api/metrics/top-artists${limit ? `?limit=${limit}` : ''}`)
